# A05I3 – Physical Time-Series Replay Implementation V01

Status: candidate, pending independent native qualification on the laptop. Predecessor: R02A-R1T1 qualified 225-source-file baseline, SHA-256 `3110F5F19C3E14A37BE3403BE1AD3B576FAF78CA05162EDE8DB690A6B20387C4`.

## Scope

- A05 `environment/replay.py` provides `ReplaySource`, `ReplayTable`, `ReplayBinding`, `ReplaySpec`, and reset-scoped `ReplaySession`.
- Built-in UTF-8 CSV and optional PyArrow Parquet readers; exact file SHA-256; typed custom `ReplayTable` boundary. Mandatory columns and source units are explicitly declared, not inferred.
- ISO timestamps, timezone-aware UTC conversion, ambiguous/nonexistent DST rejection, monotonically increasing unique timestamps; default first jointly valid source time.
- Unique common cadence inference; explicit `dt_seconds` for mixed/irregular cadence; exact/linear/ZOH alignment with optional maximum gap, no power/energy conversion.
- `mode='tile'` default, `mode='strict'` opt-in. Each independently bound source cycles its complete canonical period, including data preceding a later chosen t0; a strict episode stops on the last valid completed step. User horizon is independent of source period.
- The A05I2 `PhysicalExogenousBinding` and A03/A04 native authority are reused unchanged; one-row source selection occurs before the existing Snapshot solve. No new solution calls. Reset and first step share physical `d[0]`. No native Daily/Duty/Yearly execution.
- Time metadata/H0 and public provenance retain logical/physical sample time, source hashes, original rows/times, resampling operation, canonical indices, wrap/cycle, and replay contract hash. No actual future values are disclosed as controller forecasts.

## API example

```python
from opendsssim.environment import OpenDSSSimulator, ReplaySpec, ReplaySource, ReplayBinding
replay = ReplaySpec(
    sources=(ReplaySource('load_file', 'timestamp', 'UTC', path='load.csv'),),
    bindings=(ReplayBinding('load_file', 'load', ('Load.S1a',), 'absolute_pq',
                            ('p_kw', 'q_kvar'), ('kW', 'kvar')),),
    mode='tile', max_steps=48,
)
env = OpenDSSSimulator('path/to/IEEE123Master.dss', exogenous_replay=replay)
obs, info = env.reset()
```

`exogenous_replay` is mutually exclusive with `exogenous` and `episode_spec`; replay's `dt_seconds`, `start_time_utc`, and `max_steps` are also overridable with the existing `reset(options={...})` fields. The existing A05I2 `exogenous=` path remains unchanged. Parquet use requires `pyarrow` installed in the execution environment; there is no implicit CSV fallback.

## Qualification and limitations

- Test typed source parsing, CSV/Parquet parity (Parquet skipped with a recorded reason when PyArrow unavailable), DST errors, duplicate/NaN rejection, first valid index, mismatched cadence, linear/hold exact semantics, provenance, tile and strict endpoints.
- Test both real IEEE-123 feeder variants, first step/reset shared sample, native load readback, source-based truncation, and N+1 authoritative Snapshot solves.
- Full source-manifest preservation and three fresh independent complete regression processes.
- This does NOT implement A05I4 forecasts, A05I5 noise, dynamic events, controller truth access, automatic energy aggregation, interpolation across a tile seam, or global serializer changes. R01/R02 remain open as reliability concerns, separately recorded even if regression passes.
- Exact alignment is fail-closed when an explicitly selected origin is not on the source's canonical grid; arbitrary phase-shifting/aggregation of heterogeneous timestamp grids requires separate design qualification.
