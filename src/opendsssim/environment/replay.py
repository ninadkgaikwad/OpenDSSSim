"""A05I3 deterministic, physical-only CSV/Parquet exogenous replay.

Parses all required input and checks bindings before any plant write.  Data
indices and logical UTC clock remain distinct; truth is not a forecast and
never enters a controller action channel. No native DSS time-series modes.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import csv
import json
import math

from .clock import EpisodeClockError, EpisodeSpec, _utc
from .exogenous import ExogenousProfileSpec, LoadSeries, PVSeries


class ReplayValidationError(ValueError):
    """A05I3 source, time, binding or interpolation preflight failure."""


@dataclass(frozen=True, slots=True)
class ReplayTable:
    """Custom-reader boundary: same immutable, hashed, raw typed table as files.

    Reader implementations may construct this object, but have no backend
    reference or executable callback inside a simulator step.
    """
    timestamps: tuple[str | datetime, ...]
    columns: Mapping[str, tuple[Any, ...]]
    content_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.timestamps, (tuple, list)) or not self.timestamps:
            raise ReplayValidationError("ReplayTable needs nonempty timestamps")
        object.__setattr__(self, "timestamps", tuple(self.timestamps))
        if not isinstance(self.columns, Mapping) or not self.columns:
            raise ReplayValidationError("ReplayTable needs named columns")
        result = {}
        for k, values in self.columns.items():
            if not isinstance(k, str) or not k or k in result or not isinstance(values, (tuple, list)) or len(values) != len(self.timestamps):
                raise ReplayValidationError("ReplayTable invalid column identity or length")
            result[k] = tuple(values)
        object.__setattr__(self, "columns", MappingProxyType(result))
        if (not isinstance(self.content_sha256, str) or len(self.content_sha256) != 64
                or any(x not in "0123456789abcdefABCDEF" for x in self.content_sha256)):
            raise ReplayValidationError("Custom table needs a 64-digit source SHA256")


@dataclass(frozen=True, slots=True)
class ReplaySource:
    source_id: str
    timestamp_column: str
    timezone_name: str
    path: str | Path | None = None
    table: ReplayTable | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise ReplayValidationError("source_id required")
        if not isinstance(self.timestamp_column, str) or not self.timestamp_column.strip():
            raise ReplayValidationError("timestamp_column required")
        if not isinstance(self.timezone_name, str) or not self.timezone_name.strip():
            raise ReplayValidationError("Explicit source timezone required")
        if (self.path is None) == (self.table is None):
            raise ReplayValidationError("Exactly one file path or validated custom ReplayTable required")
        if self.path is not None and Path(self.path).suffix.lower() not in {".csv", ".parquet"}:
            raise ReplayValidationError("Only CSV or Parquet built-in readers are supported")


@dataclass(frozen=True, slots=True)
class ReplayBinding:
    """Explicit A05I2 physical binding; no guessing from column names.

    load absolute_pq: (kW, kvar), multiplier: (pu,), p_signed_pf:
    (kW, signed_pf). PV: (irradiance_kw_m2,) or (irradiance_kw_m2,
    outdoor_temperature_degC, wind_speed_m_s), paired Faiman weather.
    """
    source_id: str
    kind: str
    targets: tuple[str, ...]
    mode: str
    columns: tuple[str, ...]
    units: tuple[str, ...]
    interpolation: str = "exact"
    max_gap_seconds: float | None = None
    u0: float = 25.0
    u1: float = 6.84

    def __post_init__(self) -> None:
        if self.kind not in {"load", "pv"} or not isinstance(self.source_id, str) or not self.source_id:
            raise ReplayValidationError("Unknown binding kind or source")
        if not isinstance(self.targets, (tuple, list)) or not self.targets or any(
            not isinstance(x, str) or "." not in x or not x.strip() for x in self.targets
        ) or len({x.casefold() for x in self.targets}) != len(self.targets):
            raise ReplayValidationError("Explicit unique native Class.Name targets required")
        object.__setattr__(self, "targets", tuple(self.targets))
        if not isinstance(self.columns, (tuple, list)) or not isinstance(self.units, (tuple, list)):
            raise ReplayValidationError("Explicit column and unit tuples required")
        object.__setattr__(self, "columns", tuple(self.columns))
        object.__setattr__(self, "units", tuple(self.units))
        required = ({"absolute_pq": ("kW", "kvar"), "multiplier": ("pu",),
                     "p_signed_pf": ("kW", "signed_pf")} if self.kind == "load" else
                    {"irradiance": ("kW/m2",), "irradiance_faiman": ("kW/m2", "degC", "m/s")})
        if self.mode not in required or self.units != required[self.mode] or len(self.columns) != len(self.units):
            raise ReplayValidationError("Unqualified physical mode, declared units or column cardinality")
        if any(not isinstance(c, str) or not c for c in self.columns) or len(set(self.columns)) != len(self.columns):
            raise ReplayValidationError("Missing or repeated physical columns")
        if self.interpolation not in {"exact", "linear", "hold"}:
            raise ReplayValidationError("Only exact, declared linear and declared hold are supported")
        if self.interpolation != "exact" and self.kind == "load" and self.mode == "p_signed_pf":
            raise ReplayValidationError("Signed PF is not safely interpolated without separate qualification")
        if self.max_gap_seconds is not None and (isinstance(self.max_gap_seconds, bool)
                or not isinstance(self.max_gap_seconds, (int, float)) or
                not math.isfinite(float(self.max_gap_seconds)) or self.max_gap_seconds <= 0):
            raise ReplayValidationError("max_gap_seconds must be finite and positive")
        if self.kind == "pv":
            if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in (self.u0, self.u1)) or self.u0 <= 0 or self.u1 < 0:
                raise ReplayValidationError("Invalid Faiman coefficients")


@dataclass(frozen=True, slots=True)
class ReplaySpec:
    sources: tuple[ReplaySource, ...]
    bindings: tuple[ReplayBinding, ...]
    mode: str = "tile"
    dt_seconds: float | None = None
    start_time_utc: datetime | str | None = None
    max_steps: int | None = None

    def __post_init__(self) -> None:
        if self.mode not in {"strict", "tile"}:
            raise ReplayValidationError("Replay mode must be 'strict' or 'tile'")
        if not isinstance(self.sources, (tuple, list)) or not self.sources or not isinstance(self.bindings, (tuple, list)) or not self.bindings:
            raise ReplayValidationError("Replay requires sources and physical bindings")
        if not all(isinstance(x, ReplaySource) for x in self.sources) or not all(isinstance(x, ReplayBinding) for x in self.bindings):
            raise ReplayValidationError("Typed sources and bindings are required")
        object.__setattr__(self, "sources", tuple(self.sources))
        object.__setattr__(self, "bindings", tuple(self.bindings))
        ids = [x.source_id for x in self.sources]
        if len(ids) != len(set(ids)) or any(b.source_id not in ids for b in self.bindings):
            raise ReplayValidationError("Duplicate source IDs or unknown binding source")
        if set(ids) != {b.source_id for b in self.bindings}:
            raise ReplayValidationError("Unbound sources are not included in the replay contract")
        targets = [x.casefold() for b in self.bindings for x in b.targets]
        if len(targets) != len(set(targets)):
            raise ReplayValidationError("Multiple exogenous writers for one native endpoint")
        if self.dt_seconds is not None:
            _positive_dt(self.dt_seconds)
        if self.start_time_utc is not None:
            _utc(self.start_time_utc)
        if self.max_steps is not None and (isinstance(self.max_steps, bool)
                or not isinstance(self.max_steps, int) or self.max_steps <= 0):
            raise ReplayValidationError("max_steps must be a positive integer")


def _positive_dt(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or value <= 0:
        raise ReplayValidationError("dt_seconds must be finite and positive")
    return float(value)


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise ReplayValidationError(f"{label} is boolean")
    try:
        x = float(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ReplayValidationError(f"{label} must be numeric") from exc
    if not math.isfinite(x):
        raise ReplayValidationError(f"{label} is not finite")
    return x


def _parse_utc(raw: Any, tz_name: str) -> datetime:
    if isinstance(raw, datetime):
        stamp = raw
    elif isinstance(raw, str):
        try:
            stamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ReplayValidationError("Invalid ISO8601 timestamp") from exc
    else:
        raise ReplayValidationError("Timestamp must be ISO8601 or datetime")
    if tz_name in {"UTC", "Etc/UTC"}:
        zone = timezone.utc
    else:
        try:
            zone = ZoneInfo(tz_name)
        except ZoneInfoNotFoundError as exc:
            raise ReplayValidationError(f"Unknown timezone {tz_name}") from exc
    if stamp.tzinfo is None:
        a, b = stamp.replace(tzinfo=zone, fold=0), stamp.replace(tzinfo=zone, fold=1)
        if a.utcoffset() != b.utcoffset():
            raise ReplayValidationError("Ambiguous or nonexistent local DST timestamp")
        if a.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) != stamp:
            raise ReplayValidationError("Nonexistent local timestamp")
        stamp = a
    else:
        # Explicit-offset timestamps are sufficient to resolve fold; preserve
        # original declared-zone consistency instead of accepting contradictions.
        actual = stamp.astimezone(zone)
        if actual.utcoffset() != stamp.utcoffset():
            raise ReplayValidationError("Timestamp offset conflicts with declared timezone")
    return stamp.astimezone(timezone.utc)


def _load_source(src: ReplaySource) -> tuple[tuple[datetime, ...], Mapping[str, tuple[Any, ...]], str]:
    if src.table is None:
        p = Path(src.path)
        if not p.is_file():
            raise ReplayValidationError(f"Source file unavailable: {p}")
        raw = p.read_bytes()
        digest = sha256(raw).hexdigest().upper()
        if p.suffix.lower() == ".csv":
            try:
                reader = csv.DictReader(raw.decode("utf-8-sig").splitlines())
                if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
                    raise ReplayValidationError("Missing or duplicate CSV column names")
                rows = tuple(reader)
            except (UnicodeDecodeError, csv.Error) as exc:
                raise ReplayValidationError("Invalid UTF-8 CSV") from exc
            if not rows or any(None in row for row in rows):
                raise ReplayValidationError("Empty CSV or inconsistent column cardinality")
            cols = {name: tuple(row[name] for row in rows) for name in reader.fieldnames}
        else:
            try:
                import pyarrow.parquet as pq
            except ImportError as exc:
                raise ReplayValidationError("Parquet requires pyarrow; no silent format fallback") from exc
            try:
                table = pq.read_table(p)
                if len(table.schema.names) != len(set(table.schema.names)):
                    raise ReplayValidationError("Duplicate Parquet columns")
                cols = {name: tuple(table[name].to_pylist()) for name in table.schema.names}
            except Exception as exc:
                raise ReplayValidationError("Unable to load Parquet into typed table") from exc
        if src.timestamp_column not in cols:
            raise ReplayValidationError(f"Missing timestamp column {src.timestamp_column}")
        stamps_raw = cols.pop(src.timestamp_column)
    else:
        stamps_raw = src.table.timestamps
        cols = dict(src.table.columns)
        digest = src.table.content_sha256.upper()
        if src.timestamp_column in cols:
            raise ReplayValidationError("Custom table timestamps must not also appear as value column")
    if not stamps_raw:
        raise ReplayValidationError("Required source has no rows")
    times = tuple(_parse_utc(value, src.timezone_name) for value in stamps_raw)
    if any(a >= b for a, b in zip(times, times[1:])):
        raise ReplayValidationError("Unsorted or duplicate UTC timestamp")
    return times, cols, digest


def _seconds(value: timedelta) -> float:
    return value.total_seconds()


def _lookup(times: tuple[datetime, ...], values: tuple[tuple[float, ...], ...], stamp: datetime,
            binding: ReplayBinding) -> tuple[tuple[float, ...], Mapping[str, Any]]:
    j = bisect_left(times, stamp)
    if j < len(times) and times[j] == stamp:
        return values[j], {"row_index": j, "source_timestamp_utc": times[j].isoformat(), "operation": "exact"}
    if binding.interpolation == "exact":
        raise ReplayValidationError("Required exact sample absent at selected grid timestamp")
    if j == 0 or j == len(times):
        raise ReplayValidationError("No interpolation or hold beyond source support")
    before, after = times[j-1], times[j]
    gap = _seconds(after-before)
    if binding.max_gap_seconds is not None and gap > binding.max_gap_seconds:
        raise ReplayValidationError("Interpolation gap exceeds declared maximum")
    if binding.interpolation == "linear":
        fraction = _seconds(stamp-before) / gap
        out = tuple(x + (y-x)*fraction for x, y in zip(values[j-1], values[j]))
    elif binding.interpolation == "hold":
        fraction = 0.0
        out = values[j-1]
    else:
        raise ReplayValidationError("Unsupported interpolation method")
    if not all(math.isfinite(x) for x in out):
        raise ReplayValidationError("Interpolated value is nonfinite")
    return out, {"row_index": j-1, "next_row_index": j, "source_timestamp_utc": before.isoformat(),
                 "next_source_timestamp_utc": after.isoformat(), "operation": binding.interpolation,
                 "linear_weight": fraction if binding.interpolation == "linear" else None}


class ReplaySession:
    """Prevalidated finite per-source canonical samples, cycled only by index."""

    def __init__(self, config: ReplaySpec, *, options: Mapping[str, Any] | None = None):
        opts = {} if options is None else dict(options)
        if set(opts) - {"start_time_utc", "dt_seconds", "max_steps"}:
            raise ReplayValidationError("Unsupported A05I3 reset option")
        source = {s.source_id: _load_source(s) for s in config.sources}
        cadences = []
        for times, _, _ in source.values():
            intervals = [_seconds(b-a) for a, b in zip(times, times[1:])]
            if intervals and all(math.isclose(x, intervals[0], abs_tol=1e-8, rel_tol=0) for x in intervals):
                cadences.append(intervals[0])
            else:
                cadences.append(None)
        raw_dt = opts.get("dt_seconds", config.dt_seconds)
        if raw_dt is None:
            if any(x is None for x in cadences) or len(set(cadences)) != 1:
                raise ReplayValidationError("No unambiguous common cadence: explicit dt required")
            raw_dt = cadences[0]
        dt = _positive_dt(raw_dt)
        cadence_by_id = dict(zip(source.keys(), cadences))
        for binding in config.bindings:
            cadence = cadence_by_id[binding.source_id]
            if cadence is not None and cadence > dt + 1e-8 and binding.interpolation == "exact":
                raise ReplayValidationError("Upsampling requires declared interpolation or hold")
        earliest = max(times[0] for times, _, _ in source.values())
        explicit_start = opts.get("start_time_utc", config.start_time_utc)
        if explicit_start is None:
            # Select the earliest *jointly valid* time, not simply the latest
            # source start. Exact bindings constrain candidate timestamps;
            # interpolated/held bindings validate coverage at those candidates.
            exact_bindings = [b for b in config.bindings if b.interpolation == "exact"]
            if exact_bindings:
                candidates = (t for t in source[exact_bindings[0].source_id][0] if t >= earliest)
                start = None
                for candidate in candidates:
                    if all(source[b.source_id][0][0] <= candidate <= source[b.source_id][0][-1]
                           and (b.interpolation != "exact" or candidate in source[b.source_id][0])
                           for b in config.bindings):
                        start = candidate
                        break
                if start is None:
                    raise ReplayValidationError("No jointly valid timestamp across required sources")
            else:
                start = earliest
        else:
            start = _utc(explicit_start)
        if start < earliest:
            raise ReplayValidationError("Selected origin precedes jointly available required data")
        horizon = opts.get("max_steps", config.max_steps)
        self.episode_spec = EpisodeSpec(start, dt, horizon)
        self.mode = config.mode
        self._config = config
        self._samples: dict[str, tuple[tuple[tuple[float, ...], Mapping[str, Any]], ...]] = {}
        self._binding_by_key: dict[str, ReplayBinding] = {}
        self._initial_indices: dict[str, int] = {}
        self._source_hashes = {s: data[2] for s, data in source.items()}
        for pos, binding in enumerate(config.bindings):
            key = str(pos)
            times, cols, _digest = source[binding.source_id]
            for col in binding.columns:
                if col not in cols:
                    raise ReplayValidationError(f"Missing required {binding.source_id} column {col}")
            rows = tuple(tuple(_number(cols[col][i], f"{binding.source_id}.{col}[{i}]")
                               for col in binding.columns) for i in range(len(times)))
            # A05I2 typed constructors validate physical domains again per sample.
            # Replay the *entire* original source period, including valid
            # data before t0, so tile cycles back to its true first sample.
            offset = _seconds(start - times[0]) / dt
            initial = round(offset)
            if initial < 0 or not math.isclose(offset, initial, rel_tol=0, abs_tol=1e-8):
                raise ReplayValidationError("Selected origin is not aligned to the declared source grid")
            valid = []
            stamp = times[0]
            while stamp <= times[-1]:
                val, rowprov = _lookup(times, rows, stamp, binding)
                _make_series(binding, val)
                valid.append((val, rowprov))
                try:
                    stamp = times[0] + timedelta(seconds=len(valid) * dt)
                except OverflowError as exc:
                    raise ReplayValidationError("Source time exceeds datetime range") from exc
            if not valid or initial >= len(valid):
                raise ReplayValidationError("Source has no jointly valid sample")
            self._samples[key] = tuple(valid)
            self._initial_indices[key] = initial
            self._binding_by_key[key] = binding
        self.strict_sample_count = min(len(series) - self._initial_indices[key]
                                       for key, series in self._samples.items())
        fingerprint = {"schema": "A05I3.replay.v1", "mode": self.mode, "t0": start.isoformat(),
                       "dt_seconds": dt, "source_hashes": self._source_hashes,
                       "bindings": [{"source_id": b.source_id, "kind": b.kind, "mode": b.mode,
                                    "targets": b.targets, "columns": b.columns, "units": b.units,
                                    "interpolation": b.interpolation, "max_gap_seconds": b.max_gap_seconds,
                                    "u0": b.u0, "u1": b.u1} for b in config.bindings]}
        self.identity_sha256 = sha256(json.dumps(fingerprint, sort_keys=True, separators=(",", ":")).encode()).hexdigest().upper()

    def last_strict_index(self, index: int) -> bool:
        return self.mode == "strict" and index == self.strict_sample_count-1

    def sample(self, index: int) -> tuple[ExogenousProfileSpec, dict[str, Any]]:
        if not isinstance(index, int) or index < 0:
            raise ReplayValidationError("Replay sample index must be nonnegative")
        loads, pvs, entries = [], [], []
        for key, series in self._samples.items():
            binding = self._binding_by_key[key]
            absolute = self._initial_indices[key] + index
            if self.mode == "strict" and absolute >= len(series):
                raise ReplayValidationError("A05I3_REQUIRED_SOURCE_EXHAUSTED")
            j = absolute % len(series) if self.mode == "tile" else absolute
            values, row = series[j]
            obj = _make_series(binding, values)
            (loads if binding.kind == "load" else pvs).append(obj)
            entries.append({"source_id": binding.source_id, "source_sha256": self._source_hashes[binding.source_id],
                            "kind": binding.kind, "targets": list(binding.targets),
                            "canonical_index": j, "canonical_count": len(series),
                            "initial_canonical_index": self._initial_indices[key],
                            "replay_cycle": absolute//len(series) if self.mode == "tile" else 0,
                            **dict(row)})
        spec = ExogenousProfileSpec("A05I3:" + self.identity_sha256, tuple(loads), tuple(pvs))
        return spec, {"replay_mode": self.mode, "replay_sha256": self.identity_sha256,
                      "logical_index": index, "sources": entries}


def _make_series(binding: ReplayBinding, values: tuple[float, ...]) -> LoadSeries | PVSeries:
    if binding.kind == "load":
        point = values[0] if binding.mode == "multiplier" else values
        return LoadSeries(binding.targets, binding.mode, (point,))
    return PVSeries(binding.targets, (values[0],),
                    None if len(values) == 1 else (values[1],),
                    None if len(values) == 1 else (values[2],), binding.u0, binding.u1)
