# OpenDSSSim A05 V1 — Engineering Closeout and Conditional Source Freeze

**Date:** 2026-11-04  
**Artifact scope:** Documentation only. This document does not modify runtime code and is not an unconditional reliability or production-release sign-off.  
**Evidence basis:** A05I6R2 inline qualified successor, installed 243-file manifest, and independent review of the targeted and fresh-process regression logs.

## 1. Qualification decision and exact frozen source identity

- **Engineering qualification decision:** **PASS** for the defined A05I1–A05I6 simulator-interface and integration test scope.
- **Authoritative pre-closeout source manifest:** `F4D663B951A56209F80E18F4832CCA47E6CB24B6090EA730528D51A25440A8CF` (243 files).
- **A05I6R2 evidence archive:** `OpenDSSSim_A05I6R2_Inline_20261104T200632615Z.zip`; archive SHA-256 `90C35751770DB6ABCAD146FD6B98399B08A1F0B25F17BED504EED5E7D9696C14`.
- **Reported and independently reviewed native gates:** targeted `99/99` PASS; complete repository regression `187/187` PASS in each of three distinct fresh processes. All reported skipped tests 0 and JSON decoding failures 0; source hashes checked after each run.
- **A05I6R2 delta:** one integration test replacement and one Markdown traceability addition; **no R2 runtime changes**. The release explicitly retains the A05I6 controller-context runtime as installed at A05I6 V01.
- **Documentation-only closeout installation:** adds this file and the B00 native-control time-series baseline contract, with no replacements or deletions. It obtains a *separate* 245-file documentation successor manifest and receipt only after guarded installation. The frozen engineering/runtime identity remains traceable to the 243-file qualified predecessor.

## 2. Supported A05 V1 mechanisms and scope

| Stage | Qualified mechanism | Scope qualification |
|---|---|---|
| A05I1 | External Option-A episode clock and immutable temporal hook context | `reset` samples and solves at t[0]; first `step` acts using d[0], then advances logical decision time |
| A05I2 | Typed physical load/P/Q/signed-PF and PV irradiance / temperature mappings | Physical truth applied to existing Plant before authoritative Snapshot solve; preserves native limits and A03 semantics |
| A05I3 | CSV/Parquet timestamped replay, UTC/DST and interpolation, strict/tile, provenance | Same source used for truth across decision epochs; no independent load controller |
| A05I4 | Same-source perfect forecast oracle | Explicit authorized load/PV forecast, no backend write/solve or clock advance |
| A05I5 | Seeded forecast error | No noise or seeded additive Gaussian with domain bounds; only controller-visible forecast altered, physical actuals untouched |
| A05I6 | Detached controller-facing context | Current A04-permitted observation, time, static network, selected device statuses, authorized forecast and action feedback |
| A04 integration | ProblemSpec, Gym Dict spaces, action authorization, requested/applied/realized feedback | Only `env.step(a_req)` may effect authorized supervisor commands |

**Solver accounting:** for N completed actions under the current time contract, expected authoritative Snapshot solves are one reset solve plus N step solves. The native power-flow control iterations inside a Snapshot are not *additional external* simulator `solve_snapshot()` calls; record both counts separately.

## 3. Preserved architecture and exclusions

- **Plant owns native physics and writes.** Controllers are separate clients of `controller_context()`/authorized observations and `env.step(action)`; do not give them raw backend access or mutation authority.
- **No dynamic exogenous faults, outages, repairs, topology changes, or external enable/disable events** are part of A05 V1. Static initial faults/health from A04 persist. Authorized controller-requested switch actions under A04 remain in scope.
- **No controller-facing privilege expansion:** A05 forecasts are not inserted into the frozen A04 Gym observation schema; A05I6 exposes a separate optional controller context.
- **No validated production RBC/MPC/RL algorithms:** P1/P2 contract and experiment assets are present, but generalized RBC, Gurobi MPC and SB3-compatible Branching Dueling DDQN source implementations were not installed in the 243-file qualified manifest. A05I6 tests use controlled test clients.
- **No universal feeder/signal claim:** real integration tests exercised both repository IEEE-123 feeder variants with selected load and PV devices, but not exhaustive device coverage, all control actions, long horizons or production campaigns.
- The 56 inventoried but unmanifested files seen during recent tree collections (including P2 work) were **not** included in the 243-file source baseline; they were not erased, modified or silently promoted into the freeze.

## 4. Reliability register — unresolved

| Concern | Observed result | Release consequence |
|---|---|---|
| **R01** Windows/AltDSS native `0xe0465043` exception traces | Eight traces per pytest process persisted even when tests exited 0 | **OPEN**. No assertion of backend process stability or production readiness. Investigate before a clean production release. |
| **R02** Intermittent `Capacitor.cap1` full-property JSON corruption | A separate narrowly scoped R02A sparse/typed capacitor serialization mitigation qualified; current A05I6R2 campaign reported no JSONDecodeError | **OPEN, MITIGATION QUALIFIED**. Absence in three regressions does not prove extinction. |

**Sign-off category:** *A05 V1 source/engineering capability freeze, with explicit reliability exceptions.* A separate reliability disposition and release authorization are necessary before claiming an unrestricted production freeze.

## 5. Controller handoff / B00 native-control baseline

The simulator API is ready for **adapter development and native reference simulation**, not for claims that RBC/MPC/RL are already integrated. Implement B00 first using the separate contract `docs/development/control_science/common/B00_Native_Control_TimeSeries_Baseline_Contract_20261104.md`, then follow capability-based P1 and P2 controller science work. Avoid changes to the qualified A05/A04 implementation for this first baseline. New source development must begin with current repository-tree and directed-content inspection, and pass genuinely native IEEE-123 tests.

## 6. Closeout validation and provenance

A guarded documentation-only installer must reject modified/missing predecessor files, altered qualified evidence, existing destination files and unexpected payload hashes. Its generated receipt and 245-file successor manifest are *administrative artifacts*, not independent proof that runtime physics changed or that R01/R02 have closed. No Pytest/AltDSS work is required to assert **documentation-only byte preservation**, but B00 native-controls operation requires a separate qualification campaign.
