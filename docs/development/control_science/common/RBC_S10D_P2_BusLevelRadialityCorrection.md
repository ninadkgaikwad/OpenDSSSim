# S10D — Controller-only phase-disjoint regulator corridor correction

## Provenance and authority

Predecessor: qualified RBC S09A 331-file source manifest SHA256 `9BCB14EC9551E18E45A93751B3F5ECB029517F65082BE62B2A1B9C910F0975C3`.
Fresh tree S10A SHA256 `4C87652C1E30495D47402A649792F381BD02EBF8A3C250CCE397A0964E48870E` and fresh directed S10B SHA256 `2DD98724E846BBE9B46C9C9C36E05C5E0E5EF0413B8A8A352B6AD695A9F77707`; independently reviewed. Read-only S10C did not change source.

The P2 controller's bus-level `_graph` helper represented each 1-phase regulator between the same two buses as a parallel bus edge, incorrectly marking energized circuits as cyclic. Ratified P2 MF01 and MF02 share multi-phase regulator banks where reg3a/reg3c (25/25r) and reg4a/reg4b/reg4c (160/160r) connect distinct phases. Source-evidence reproduction of this bug found three spurious cycle edges, and correct bus-level corridor grouping gave 84 of 91 loads for MF01 and 91 of 91 for MF02 A/B/C. The invalid all-ties-closed MF02 configuration still contains a true line cycle.

## Strict remedy and safety

Only `src/opendsssim/controllers/reference/p2_graph.py` is replaced. The helper `_phase_disjoint_regulator_corridor` recognizes 1-phase transformer terminals with matching explicitly numbered phases 1, 2 or 3 and identical endpoint buses. For bus-level topology checking only, edges of disjoint phases across the same two physical buses count once. Duplicate same-phase transformers, other lines, ambiguous phases, and all genuinely parallel corridors still count separately and can cause cycles. This does not merge real network impedances or alter AltDSS. No simulator core, feeder files, fault masks, control contracts or science formula is changed.

The correction **is not** a phase-aware connectivity/radiality certificate; native state readback, voltage screening, and operational thermal/priority/curtailability data remain independent. P2 never emits an action without the authorized A04 action path and qualified evaluator. This is a bounded P2 *voltage-only* native experiment, not full frozen MPC/RL comparison or thermal certification.

## Testing and evidence

Add `tests/unit/controllers/test_s10d_phase_parallel_graph.py` (phase-distinct corridor, same-phase true cycle, line tie cycle, fault disconnection, ambiguous phase). Rerun S09 pure/native, B00 integration, and three full pytest regressions. Run a detached native P2-only campaign through the existing S10C orchestrator after the source correction. Preserve 331/331 predecessor and post-repair successor identities, original S10C P1 results, action audits, route selection, timeseries, HTML results and native shadow-screen receipts in Downloads.

If native P2 pilot or regression fails, STOP; preserve evidence, no automatic rollback/reinstall. Future repair requires fresh tree and fresh directed collection.
