# OpenDSSSim A05I6 — Controller Information Integration V01

**Status:** IMPLEMENTATION CANDIDATE, not qualified/frozen until native acceptance.
**Predecessor:** 237-file independently qualified A05I5 SHA256 `DE8B77E8E745CA020280B21D73778A949A03FF50C0BA14C7F09BA25956C6DEC5`.
**Source selection:** 196 verified files from A05I6 directed evidence of 2026-11-03.
**Reliability register:** R01 Windows native exception traces OPEN; R02 intermittent capacitor JSON OPEN (R02A mitigation qualified).

## Implementation boundary

- **REUSE without modifications:** A05I1 clock/hook context, A05I2 physical exogenous writer, A05I3 CSV/Parquet replay, A05I4 oracle, A05I5 seeded error, A03 semantics, A04 authority/Gym/ProblemSpec, R02A backend, feeders.
- **ADAPT:** `environment/simulator.py` adds only an official `controller_context(...)` read-only service. `environment/__init__.py` exports the new types. Existing reset/step signatures, Gym spaces, physical actions, and H0–H3 history remain untouched.
- **NEW:** `environment/controller_context.py` holds detached, immutable public snapshots; native and unit acceptance tests, and this contract.
- **Controllers:** No RBC/MPC/RL P1/P2 policy implementations are present in the qualified repository. Tests use small controlled clients and do not claim controller-algorithm completion.

## `env.controller_context` contract

This request requires a committed, active episode and returns a `ControllerContext` with:

1. A deeply detached and recursively read-only copy of the canonical A04-permitted *current* Gym observation; unchanged observation/action space SHA256 identities and canonical action-layout metadata.
2. Episode ID, completed steps, current **decision** time and latest **electrical sample** time, distinctly.
3. Optional **single-trajectory** A05I4/A05I5 forecast, derived only by calling the existing `env.exogenous_forecast`; selectors, required/optional strict-coverage behavior and seeded repeatability therefore inherit their original contracts. No forecast by default.
4. Public **static** inventory topology (buses, phase counts, element terminal-bus mapping, possible source buses), not dynamic future connectivity or future equipment health. Static source buses are *candidates*; a controller chooses its power-flow abstraction.
5. Current device `Enabled` readback **only** for A04-selected inventory object identities. Known A04 static faults report `FAULTED`; without a fault sensor, other devices report `UNKNOWN`, **never fabricated HEALTHY**. Effective commandability distinguishes external-authorized, disabled, fault-locked, native-owned and unavailable states. Requests for unselected device status fail closed.
6. Only prior realized action *feedback* and status (not private full state or unverified action requests).

`ControllerContext` is an immutable value object. Its `to_dict()` creates an independent mutable copy for serialization. No Python object from Plant, backend, EpisodeClock, runtime history, original replay, trusted Gaussian audit, or native solver is exposed through the returned context. This is an **official-interface** protection, not a security sandbox against intentional Python private-attribute access.

## Deliberate V1 limitations / freeze conditions

- Frozen A04 `ProblemSpec.observations.forecast_groups` currently raises `A05DeferredError`; therefore this patch **does not inject an undeclared forecast tensor into Gym**. Read-only forecast access is qualified through the explicit controller service only. An observation-embedded forecast requires a separately authorized A04 contract extension with shape/unit declarations; do not claim this route implemented.
- The baseline metadata inventory has structural topology, but no qualified dynamic health sensor, ampacity/rating catalog, or live switch topology observer. Do not label structural topology as current energized graph, invent health, or claim unsupported ratings.
- Existing trusted H0–H3 diagnostics and engine-native exception traces are not altered. No global security sandbox, new logs, events, fault/repair scheduling, or additional Snapshot solves are introduced.
- The final A05 design's controller-side transformations and P1/P2 scientific algorithms remain separate development work. A qualified A05I6 simulator API is not equivalent to qualified RBC/MPC/RL algorithms.

## Native acceptance / scientific invariants

- Full 237-file predecessor verification and exact payload hashes; no unlisted source modifications; successor and rollback hashes.
- Targeted tests and **three fresh full-repository regressions**, zero skipped tests, zero JSON decoding errors; R01 traces separately recorded (not swallowed).
- Genuine canonical and working IEEE-123 AltDSS snapshots, multi-load replay, working-feeder multi-PV, seeded forecast consistency, controller-visible consent and denied status selectors, PV Q action through `env.step`, zero context forecast writes/solves, clock alignment, unchanged Gym shapes and H0–H3 behavior.
- Explicitly retain R01/R02 in evidence; native closeout does **not** close those issues.
