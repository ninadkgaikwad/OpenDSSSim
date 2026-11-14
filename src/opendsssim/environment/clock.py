"""A05 external episode clock and immutable temporal hook context.

The physical backend remains a Snapshot power-flow engine. This clock is the
authoritative *logical* time for Gym reset/step and cannot command AltDSS.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import math
from numbers import Integral, Real
from types import MappingProxyType
from typing import Any, Mapping

from opendsssim.runtime.history import RuntimeHistory
from opendsssim.runtime.schema import RuntimeStepContext


GENERIC_ORIGIN_UTC = datetime(2000, 1, 1, tzinfo=timezone.utc)


class EpisodeClockError(ValueError):
    """Invalid or unavailable A05 episode/clock selection."""


def _freeze_time(value: Any) -> Any:
    """Freeze A05 temporal metadata, including future nested source identities.

    Time metadata is JSON-shaped; rejecting arbitrary mutable objects prevents
    an imported A04 hook from gaining a mutable handle through this A05 field.
    """
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze_time(v) for k, v in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze_time(v) for v in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Unsupported temporal metadata value: {type(value).__name__}")


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalRuntimeStepContext(RuntimeStepContext):
    """A05-only extension preserving the frozen A04 hook/context contract.

    Every existing A04 hook still receives a RuntimeStepContext instance. The
    additional ``time`` field is immutable and contains the precise current
    electrical sample and next decision timestamps before hooks execute.
    """

    time: Mapping[str, Any]

    @classmethod
    def create(cls, *, time: Mapping[str, Any], **kwargs: Any) -> "TemporalRuntimeStepContext":
        if not isinstance(time, Mapping):
            raise TypeError("TemporalRuntimeStepContext requires time metadata mapping")
        kwargs["time"] = _freeze_time(time)
        # The frozen A04 factory freezes all inherited context fields. Its
        # factory uses cls(...) and therefore constructs the A05 subclass.
        return RuntimeStepContext.create.__func__(cls, **kwargs)


class TemporalRuntimeHistory(RuntimeHistory):
    """A05-only history adapter; frozen A04 RuntimeHistory stays byte-identical."""

    def append(self, context: Any, *, phase: str, reward: Any, terminated: Any,
               truncated: Any, info: dict[str, Any], full_state: Any = None) -> None:
        super().append(context, phase=phase, reward=reward, terminated=terminated,
                       truncated=truncated, info=info, full_state=full_state)
        if "time" in info:
            # H0 retains mandatory clock identity without storing full `info`.
            self._records[-1]["time"] = deepcopy(info["time"])


def _utc(value: Any) -> datetime:
    if isinstance(value, datetime):
        candidate = value
    elif isinstance(value, str):
        try:
            candidate = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise EpisodeClockError("start_time_utc must be an ISO8601 timestamp with UTC offset") from exc
    else:
        raise EpisodeClockError("start_time_utc must be a timezone-aware datetime or ISO8601 string")
    if candidate.tzinfo is None or candidate.utcoffset() is None:
        raise EpisodeClockError("start_time_utc requires an explicit UTC offset; local/DST interpretation is deferred to A05I3")
    return candidate.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class EpisodeSpec:
    """Explicit A05I1 episode parameters; generic defaults have no data source."""

    start_time_utc: datetime = GENERIC_ORIGIN_UTC
    dt_seconds: float = 3600.0
    max_steps: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "start_time_utc", _utc(self.start_time_utc))
        if (isinstance(self.dt_seconds, bool) or not isinstance(self.dt_seconds, Real)
                or not math.isfinite(float(self.dt_seconds)) or float(self.dt_seconds) <= 0):
            raise EpisodeClockError("dt_seconds must be a finite positive number")
        object.__setattr__(self, "dt_seconds", float(self.dt_seconds))
        if self.max_steps is not None and (
            isinstance(self.max_steps, bool) or not isinstance(self.max_steps, Integral)
            or int(self.max_steps) <= 0
        ):
            raise EpisodeClockError("max_steps must be a positive integer or None")
        if self.max_steps is not None:
            object.__setattr__(self, "max_steps", int(self.max_steps))

    def with_reset_options(self, options: Mapping[str, Any] | None) -> "EpisodeSpec":
        if options is None:
            return self
        if not isinstance(options, Mapping):
            raise EpisodeClockError("reset options must be a mapping")
        allowed = {"start_time_utc", "dt_seconds", "max_steps"}
        extra = set(options).difference(allowed)
        if extra:
            raise EpisodeClockError(f"Unsupported A05I1 reset option(s): {sorted(extra)!r}")
        fields = dict(options)
        if "start_time_utc" in fields:
            fields["start_time_utc"] = _utc(fields["start_time_utc"])
        return replace(self, **fields)


@dataclass(frozen=True, slots=True)
class EpisodeClock:
    """Computed clock view; step index is committed only after successful solve."""

    spec: EpisodeSpec
    episode_id: str
    reset_seed: int | None

    def at(self, index: int) -> datetime:
        if not isinstance(index, int) or index < 0:
            raise EpisodeClockError("Clock index must be a nonnegative integer")
        try:
            return self.spec.start_time_utc + timedelta(seconds=index * self.spec.dt_seconds)
        except (OverflowError, ValueError) as exc:
            raise EpisodeClockError("Episode time exceeds representable UTC datetime") from exc

    def is_horizon_exhausted(self, completed_steps: int) -> bool:
        return self.spec.max_steps is not None and completed_steps >= self.spec.max_steps

    def metadata(self, *, phase: str, completed_steps: int) -> dict[str, Any]:
        if phase not in {"reset", "step"}:
            raise EpisodeClockError(f"Invalid clock phase: {phase!r}")
        if completed_steps < 0 or (phase == "step" and completed_steps == 0):
            raise EpisodeClockError("Invalid completed_steps for clock phase")
        interval_index = 0 if phase == "reset" else completed_steps - 1
        interval_start = self.at(interval_index)
        interval_end = self.at(interval_index + 1)
        return {
            "episode_id": self.episode_id,
            "phase": phase,
            "t0_utc": self.spec.start_time_utc.isoformat(),
            "dt_seconds": self.spec.dt_seconds,
            "max_steps": self.spec.max_steps,
            "reset_seed": self.reset_seed,
            "completed_steps": completed_steps,
            "decision_time_utc": self.at(completed_steps).isoformat(),
            "electrical_sample_time_utc": interval_start.isoformat(),
            "interval_start_utc": interval_start.isoformat(),
            "interval_end_utc": interval_end.isoformat(),
            "next_decision_time_utc": self.at(completed_steps).isoformat(),
            "clock_authority": "EXTERNAL",
            "engine_time_status": "EXTERNAL_ONLY_NOT_MIRRORED",
            "exogenous_sample_status": "NO_A05_SOURCE_BOUND",
        }
