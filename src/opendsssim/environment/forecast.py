"""A05I4 source-derived, zero-error exogenous forecast oracle.

Only A05I2/A05I3 accepted physical declarations are eligible. This module
never touches the simulator's Plant, backend, Gym observation or clock state.
Noise and observations are expressly deferred to A05I5 and A05I6.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
import math
from typing import Any, Iterable

from .clock import EpisodeClock
from .exogenous import ExogenousProfileSpec, LoadSeries, PVSeries
from .replay import ReplaySession, ReplaySpec, ReplayValidationError


class ForecastError(ValueError):
    """A05I4 request violates the forecast contract."""


class ForecastUnavailableError(ForecastError):
    """There is no eligible qualified exogenous source."""


class ForecastCoverageError(ForecastError):
    """At least one required lead lies outside strict/finite source coverage."""


class ForecastSelectionError(ForecastError):
    """An explicitly requested source channel or native entity is unavailable."""


@dataclass(frozen=True, slots=True)
class ForecastValue:
    episode_id: str
    issue_time_utc: str
    decision_index: int
    lead_index: int
    valid_interval_start_utc: str
    valid_interval_end_utc: str
    channel_id: str
    entity_id: str
    value: float
    unit: str
    source_id: str
    source_sha256: str
    binding_id: str
    canonical_index: int
    replay_cycle: int
    source_timestamp_utc: str | None
    source_row_index: int | None
    resampling_operation: str
    forecast_mode: str = "oracle_perfect_exogenous"
    noise_sigma: float | None = None
    boundary_policy: str | None = None
    was_clipped: bool = False


@dataclass(frozen=True, slots=True)
class ForecastResult:
    status: str
    episode_id: str
    decision_index: int
    issue_time_utc: str
    horizon: int
    replay_mode: str
    binding_identity_sha256: str | None
    values: tuple[ForecastValue, ...]
    reason: str | None = None
    forecast_mode: str = "oracle_perfect_exogenous"
    noise_mode: str = "none"
    noise_config_sha256: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-compatible public representation."""
        from dataclasses import asdict
        return asdict(self)


_CHANNELS = {
    ("load", "absolute_pq"): (("load.kw", "kW"), ("load.kvar", "kvar")),
    ("load", "multiplier"): (("load.multiplier", "pu"),),
    ("load", "p_signed_pf"): (("load.kw", "kW"), ("load.signed_pf", "signed_pf"), ("load.kvar", "kvar")),
    ("pv", "irradiance"): (("pv.irradiance", "kW/m2"), ("pv.cell_temperature", "degC")),
    ("pv", "irradiance_faiman"): (("pv.irradiance", "kW/m2"), ("pv.outdoor_temperature", "degC"),
                                    ("pv.wind_speed", "m/s"), ("pv.cell_temperature", "degC")),
}


def _positive_horizon(raw: Any) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int) or raw <= 0:
        raise ForecastError("A05I4 horizon must be a positive integer")
    return raw


def _selector(raw: Iterable[str] | None, label: str) -> tuple[str, ...] | None:
    if raw is None:
        return None
    if isinstance(raw, (str, bytes)):
        raise ForecastSelectionError(f"{label} must be a tuple/list of exact names")
    try:
        items = tuple(raw)
    except TypeError as exc:
        raise ForecastSelectionError(f"{label} must be a tuple/list of names") from exc
    if not items or any(not isinstance(x, str) or not x.strip() for x in items):
        raise ForecastSelectionError(f"{label} must contain nonempty names")
    if len({x.casefold() for x in items}) != len(items):
        raise ForecastSelectionError(f"{label} has repeated names")
    return tuple(x.casefold() for x in items)


def _source_channels(physical: ExogenousProfileSpec, replay: ReplaySpec | None):
    """Yield declared channels only, each with a fan-out source binding."""
    if replay is None:
        declared = tuple(
            (i, "load", p.mode, physical.source_id, p)
            for i, p in enumerate(physical.loads)
        ) + tuple(
            (i + len(physical.loads), "pv",
             "irradiance_faiman" if p.outdoor_temperature_c is not None else "irradiance",
             physical.source_id, p)
            for i, p in enumerate(physical.pvs)
        )
    else:
        # ReplaySession.sample returns LoadSeries and PVSeries in separate
        # groups, whereas provenance retains the original ReplaySpec.bindings
        # order. Consume one profile of the correct kind per source binding.
        loads, pvs = iter(physical.loads), iter(physical.pvs)
        declared_list = []
        for i, binding in enumerate(replay.bindings):
            try:
                p = next(loads if binding.kind == "load" else pvs)
            except StopIteration as exc:
                raise ForecastError("A05I4 physical/replay binding cardinality mismatch") from exc
            if tuple(binding.targets) != tuple(p.targets):
                raise ForecastError("A05I4 physical/replay binding identity mismatch")
            declared_list.append((i, binding.kind, binding.mode, binding.source_id, p))
        if next(loads, None) is not None or next(pvs, None) is not None:
            raise ForecastError("A05I4 extra physical profile not bound by replay")
        declared = tuple(declared_list)
    for i, kind, mode, source_id, profile in declared:
        vals: list[float]
        if kind == "load":
            point = profile.points[0]
            if mode == "multiplier":
                vals = [float(point)]
            elif mode == "absolute_pq":
                vals = [float(point[0]), float(point[1])]
            elif mode == "p_signed_pf":
                p, pf = (float(x) for x in point)
                kvar = math.copysign(p * math.sqrt(max(0.0, 1.0-pf*pf)) / abs(pf), pf)
                vals = [p, pf, kvar]
            else:
                raise ForecastError("A05I4 unknown A05I2 load mode")
        else:
            g = float(profile.irradiance_kw_m2[0])
            if profile.outdoor_temperature_c is None:
                vals = [g, 25.0]
            else:
                ambient, wind = float(profile.outdoor_temperature_c[0]), float(profile.wind_speed_m_s[0])
                vals = [g, ambient, wind, ambient+1000.0*g/(profile.u0+profile.u1*wind)]
        if any(not math.isfinite(x) for x in vals):
            raise ForecastError("A05I4 non-finite qualified physical transform")
        for (channel, unit), value in zip(_CHANNELS[(kind, mode)], vals):
            for entity in profile.targets:
                yield i, source_id, channel, entity, value, unit


class ExogenousForecastOracle:
    """Pure read side of qualified exogenous truth. Never returns a source handle."""

    def __init__(self, *, clock: EpisodeClock, replay_session: ReplaySession | None,
                 replay_spec: ReplaySpec | None, explicit_source: ExogenousProfileSpec | None):
        if replay_session is not None and (replay_spec is None or explicit_source is not None):
            raise ForecastError("A05I4 incompatible replay/explicit source identities")
        self._clock = clock
        self._session = replay_session
        self._replay_spec = replay_spec
        self._explicit_source = explicit_source

    def request(self, decision_index: int, horizon: int, *,
                channel_ids: Iterable[str] | None = None,
                entity_ids: Iterable[str] | None = None,
                required: bool = True) -> ForecastResult:
        horizon = _positive_horizon(horizon)
        if isinstance(decision_index, bool) or not isinstance(decision_index, int) or decision_index < 0:
            raise ForecastError("A05I4 decision index must be nonnegative")
        if not isinstance(required, bool):
            raise ForecastError("A05I4 required must be boolean")
        channels = _selector(channel_ids, "channel_ids")
        entities = _selector(entity_ids, "entity_ids")
        issue = self._clock.at(decision_index).isoformat()
        replay_mode = self._session.mode if self._session else "finite_explicit"
        identity = self._session.identity_sha256 if self._session else (
            self._explicit_source.source_sha256 if self._explicit_source else None
        )
        if self._session is None and self._explicit_source is None:
            if required:
                raise ForecastUnavailableError("A05I4_NOT_CONFIGURED")
            return ForecastResult("NOT_CONFIGURED", self._clock.episode_id, decision_index,
                                  issue, horizon, "none", None, (), "A05I4_NOT_CONFIGURED")
        # Verify a full horizon before producing any public payload. Forecast
        # insufficiency must never truncate a physically valid plant episode.
        physical_points = []
        for lead in range(horizon):
            index = decision_index+lead
            if self._session is not None:
                try:
                    physical, replay_prov = self._session.sample(index)
                except ReplayValidationError as exc:
                    raise ForecastCoverageError(f"A05I4_REQUIRED_FORECAST_COVERAGE: index={index}") from exc
                sources = replay_prov["sources"]
            else:
                assert self._explicit_source is not None
                if index >= self._explicit_source.sample_count:
                    raise ForecastCoverageError(f"A05I4_REQUIRED_FORECAST_COVERAGE: index={index}")
                src = self._explicit_source
                physical = ExogenousProfileSpec(src.source_id,
                    tuple(LoadSeries(p.targets, p.mode, (p.points[index],)) for p in src.loads),
                    tuple(PVSeries(p.targets, (p.irradiance_kw_m2[index],),
                        None if p.outdoor_temperature_c is None else (p.outdoor_temperature_c[index],),
                        None if p.wind_speed_m_s is None else (p.wind_speed_m_s[index],),
                        p.u0, p.u1) for p in src.pvs))
                sources = None
            physical_points.append((physical, sources, index, lead))
        vals: list[ForecastValue] = []
        available_channels: set[str] = set()
        available_entities: set[str] = set()
        for physical, sources, index, lead in physical_points:
            start = self._clock.at(index).isoformat()
            end = self._clock.at(index+1).isoformat()
            for binding_pos, src_id, channel, entity, value, unit in _source_channels(physical, self._replay_spec):
                available_channels.add(channel.casefold())
                available_entities.add(entity.casefold())
                if channels is not None and channel.casefold() not in channels:
                    continue
                if entities is not None and entity.casefold() not in entities:
                    continue
                p = sources[binding_pos] if sources is not None else None
                source_sha = (str(p["source_sha256"]) if p is not None else
                              self._explicit_source.source_sha256)
                binding_identity = sha256(json.dumps({"source_id": src_id, "channel": channel,
                    "entity": entity, "binding_position": binding_pos, "replay_identity": identity},
                    sort_keys=True, separators=(",", ":")).encode()).hexdigest().upper()
                vals.append(ForecastValue(self._clock.episode_id, issue, decision_index,
                    lead, start, end, channel, entity, value, unit,
                    src_id, source_sha, binding_identity,
                    int(p["canonical_index"]) if p is not None else index,
                    int(p["replay_cycle"]) if p is not None else 0,
                    str(p.get("source_timestamp_utc")) if p is not None else start,
                    int(p["row_index"]) if p is not None else index,
                    str(p.get("operation", "exact")) if p is not None else "explicit"))
        if channels is not None and set(channels)-available_channels:
            raise ForecastSelectionError("A05I4 requested channel is not in the qualified source")
        if entities is not None and set(entities)-available_entities:
            raise ForecastSelectionError("A05I4 requested entity is not in the qualified source")
        if not vals:
            if required:
                raise ForecastUnavailableError("A05I4_NO_MATCHING_FORECAST_CHANNELS")
            return ForecastResult("NO_MATCH", self._clock.episode_id, decision_index,
                                  issue, horizon, replay_mode, identity, (), "A05I4_NO_MATCHING_FORECAST_CHANNELS")
        return ForecastResult("AVAILABLE", self._clock.episode_id, decision_index,
                              issue, horizon, replay_mode, identity, tuple(vals))
