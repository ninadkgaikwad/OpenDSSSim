# A05.3 - Time-Series Indexing, Resolution, and Replay

**Ratified:** 2026-10-26 (America/Los_Angeles)  
**Status:** DESIGN RATIFIED; DOCUMENTATION-ONLY; RUNTIME NOT IMPLEMENTED / NOT QUALIFIED  
**Qualified predecessor:** A05.2 documentation successor, 199 files  
**Predecessor source-manifest SHA256:** A09F067119FD12D0DDB9F07E0E703BB8874102DAC95AFC0042964B8BA40DDD36

## 1. Purpose and invariants

A05.3 connects A05.1 authoritative UTC time to A05.2 external physical inputs using deterministic file readers, sample alignment, resampling and replay. Preserve frozen A03/A04 Plant != Problem != Controller, native/external/hybrid authority, fault precedence, strict Gym action schemas, AltDSS Snapshot/STATIC operation and H0-H3 histories. Never use native Daily/Yearly/Duty runs to advance external time.

For origin t0, positive fixed duration dt and control-step index k, interval k is [t0+k*dt,t0+(k+1)*dt). Under ratified A05.1 Option A, reset performs its initial Snapshot with d[0], and step(action[k]) selects d[k], applies allowed exogenous conditions and action, performs one authoritative Snapshot, records its *actual electrical sample timestamp*, then advances the logical decision clock. Reset and first step share exactly the same d[0], including any later-qualified stochastic realization.

## 2. Input files and canonical schema (A05.3.1)

- Built-in formats: CSV and Parquet, converted to one validated in-memory tabular time-series contract. A future custom reader may return exactly this same typed contract but may not mutate AltDSS or create controller actions.
- Each source supplies a declared timestamp column, value column(s), source identifier/content SHA256 and an explicit timezone/offset. Parquet timezone-aware timestamp types are validated; CSV timestamp strings are parsed with a declared unambiguous timezone.
- All physical units and device/channel/group/phase targets come from A05.2's explicit binding, not filenames or column-name guesses. Unit conversion must be declared and qualified. Do not infer that an energy column (kWh) is an instantaneous power (kW).
- Missing mandatory columns, unknown units/target names, unsupported dtypes, ambiguous signatures and nonfinite mandatory data are fail-closed preflight errors.

## 3. Episode timestep and source resolution (A05.3.2)

One positive configurable dt in seconds controls a whole episode. In descending priority:

1. Use an explicit, valid user-selected dt when present.
2. Otherwise, infer dt only if all required timestamped sources have one demonstrably unambiguous common regular cadence.
3. Otherwise, when source cadences differ, require explicit dt plus a declared alignment/resampling method; never guess a mixed-source cadence.
4. Otherwise, **when no timestamped exogenous source exists, default dt = 3600 seconds (one hour)**, as the user ratified. A05.1's generic start remains 2000-01-01T00:00:00Z unless validly overridden.

Construct logical timestamps using integer k from t0 and dt to avoid cumulative floating-point clock drift. Invalid/irregular timestamps require A05.3.5 treatment; no native DSS time-series step is inferred.

## 4. UTC alignment and reset origin (A05.3.3)

- Canonical timestamps are timezone-aware UTC, with explicit conversion from any local source timezone. Reject ambiguous DST transitions, duplicated UTC timestamps and unsorted/invalid time axes unless an expressly declared normalization operation qualifies them.
- Following approved conversion/alignment, default t0 is the **first jointly valid timestamp across all required bound inputs**, consistent with A05.1. Optional absent channels (including the A05.2 constant-25 degC PV-temperature fallback) do not constrain t0.
- Valid user reset options may select a different jointly valid starting sample, while preserving physical input and authority checks.
- Do not silently shift independent files to manufacture an apparent common starting time. Retain original source-time identity when replaying older data under a later logical time.

## 5. Strict and tile replay (A05.3.4): **default TILE**

The user ratified both choices and explicitly chose **tile** as the default; **strict** remains opt-in. A source must first become a validated canonical regular sample array. Let source i have M_i > 0 samples, aligned initial index j_i0, and episode step k.

- **Strict:** j_i(k) = j_i0 + k, valid only while 0 <= j_i(k) < M_i. When strict required data ends, report truncation on the **last valid completed step** (reason data_exhausted); never execute an extra invalid step solely to discover the boundary.
- **Tile (default):** j_i(k) = (j_i0 + k) mod M_i. Cycle over exactly M_i samples, with source replay period M_i*dt; do not duplicate the source's last endpoint at the next cycle.
- Sources may have different valid replay periods, but all follow one monotonically advancing OpenDSSSim clock. Keep each source's original timestamp/index, replay cycle number and actual logical step timestamp distinct in provenance.
- Tiling never resets the electrical plant, native controls, fault availability or clock; it never legitimizes malformed source data.

Example: sample series [10,20,30,40], j_i0=0 and six desired steps. Strict uses [10,20,30,40] before truncation. Tile uses [10,20,30,40,10,20]; the simulation clock still advances through six unique intervals.

## 6. Interpolation and missingness (A05.3.5)

- Default: exact, finite source samples on the selected canonical grid; resampling is never silently inferred.
- Optional **linear interpolation** for semantically continuous physical signals (ordinary instantaneous P/Q, irradiance, outdoor temperature, wind speed), with valid endpoints, physical bounds and an optional declared maximum gap.
- Optional **zero-order hold** only where piecewise-constant source semantics are explicitly declared.
- No silent extrapolation beyond first/last source support in strict mode. No linear interpolation across invalid source gaps, DST ambiguities, physical discontinuities or a tile cycle seam without its own qualified explicit policy.
- Distinguish timestamp meaning: instant sample versus explicitly declared interval value. Never silently integrate/average finer-than-step power data or reinterpret energy as power; additional aggregation needs its own declared semantics and validation.
- Perform the selected transformations before physical property writes, with **zero additional authoritative solves**.

## 7. Episode duration and stop contracts (A05.3.6)

- A configured horizon N is any positive integer count of successful step calls; zero, fractional or negative N is invalid. It may be unrelated to source length.
- Reset defaults to the first jointly valid timestamp, unless a user reset-selection function supplies another validated origin.
- Under **default tile**, repeat valid data as needed until N, a user termination or a user truncation. If no finite N is configured, do not fabricate a finite data-end truncation; the caller/hook governs completion.
- Under **strict**, truncate on the last valid required sample or finite N, whichever comes first. The last valid action produces a real solve and truthful termination/truncation flags.
- Default reward = 0.0 and termination = False, with A05.1's default truncation at finite horizon/strict data boundary. Hooks never override hard source/plant safety conditions.
- For N completed actions, exactly **N+1 authoritative solves**: one reset solve plus N step solves. Required strict truth samples are d[0] through d[N-1]; do not require d[N] unless a separately declared A05.4 forecast input legitimately needs it.

## 8. Index identity, reproducibility, and failures (A05.3.7)

Retain episode ID, t0, dt, k, logical interval and next-decision times, **electrical sample timestamp**, replay mode, source/channel/target hashes, original source row/index/timestamp, canonical index, interpolation/hold operation, source replay count and applied input-vector identity. Cache keys include qualified source and time-alignment identities, not merely file paths. FAST/STANDARD/AUDIT must have identical physical/clock semantics, with appropriate H0-H3 retention. True future exogenous values are not automatically controller-visible; that restriction is formalized by A05.4/A05.6.

A failed mandatory read, interpolation, physical write, or backend solve must not commit a successful history record or advance logical time. The episode becomes inactive until reset. Do not claim atomic rollback of partial native writes.

## 9. Directed qualification required before executable A05 implementation freeze

1. CSV/Parquet parity; timestamp/units/column mapping; hashes; custom reader boundary; invalid DST and duplicate rejection.
2. Explicit dt, inferred common dt, rejected mixed cadences without dt, and **default no-data dt=3600 seconds**.
3. First common sample, reset start override, different source coverage, source timezone normalization.
4. **Default tile** with multiple source periods, seam/wrap provenance and unbroken external time; strict last-valid-step truncation.
5. Linear interpolation, zero-order hold, maximum gaps, invalid endpoints and no implicit power-energy conversion.
6. Exactly N+1 reset/step solves, shared d[0], correct true sample/decision labels and no d[N] off-by-one truth demand.
7. A04 Snapshot/STATIC and native control/fault partition unchanged; A05.2 physical bindings and source-vs-realized audit preserved.
8. H0-H3/provenance, source/caches/restart determinism and whole-predecessor regression.

**Disposition:** A05.3.1-A05.3.7 DESIGN RATIFIED, with user-selected **3600-second generic no-data timestep** and **tile replay as the default**. Only additive Markdown installation is authorized here; no A05 runtime changes or science runs. A05.4 next addresses forecast interfaces.
