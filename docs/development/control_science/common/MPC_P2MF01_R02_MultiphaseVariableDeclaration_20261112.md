# P2MF01-R02 — P2 multiphase variable declaration ordering (November 12, 2026 Pacific)

## Evidence provenance
- Frozen simulator predecessor: exact 508-file A07A3-qualified repository. No modifications to physical OpenDSS backend, plant, ProblemSpec, circuit, feeders, observables, registries, or P1 controller.
- Fresh P2MF01-R00 read-only repository tree: 530 files; 508/508 predecessor unchanged.
- P2MF01-R01 tree-derived directed source: 217/217 captured bytes match the fresh-tree manifest; evidence ZIP SHA-256 `60F0ED7DCF17476B6C579B0A4F98854D2367F6D07F66A5A74977BFFC173B9B54`.
- MF01 prior failure: Python `KeyError: ('Line.l10', 2, 0)` in `src/opendsssim/controllers/mpc/p2_milp.py` during model assembly. `m.optimize()` never reached; no AC env.step; no feasibility conclusion.

## Defect and minimum correction
For every branch `e` and prediction index `k`, the original P2 solver was creating `P[e,ph,k]` and `Q[e,ph,k]` inside the same phase loop that built the coupled multiphase voltage-drop equality. That voltage-drop expression sums `r[i][j] P[e,p_j,k] + x[i][j] Q[e,p_j,k]` over **all** phases of `e`, including phase variables not yet declared.

The R02 repair splits the loop into two passes: first declare all `P` and `Q` variables for the branch and time index, then add **unchanged** on/off power bounds, coupled voltage-drop Big-M inequalities, and optional thermal facets for every phase. No new decision variables, constraints, estimated impedances, relaxations, or objective changes are introduced.

## Scope and scientific boundaries
- Modified existing source: `src/opendsssim/controllers/mpc/p2_milp.py` ONLY.
- Add-only: one targeted regression-test module and this note. Expected 508 → 510 source files.
- Faulted-switch enforcement, source-connectivity flow, bus-level radiality, power balance, lexicographic operational slack/unserved energy/switching objectives, and action-encoding remain unchanged.
- P2 MF01 Simple and MF02 Exotic use their existing frozen IEEE-123 configurations and captured horizon-2 LinDistFlow case data. No new thermal security claim; `voltage_only_exploratory` remains authoritative.
- Mock/solver-independent construction tests verify no out-of-order phase references and verify expression coupling, while native qualification runs **real Gurobi** for P2 A02 smoke and the captured MF01+MF02 2-step optimization cases. Do not treat the mock as a solver.
- Actual 24-step official OpenDSSSim/AltDSS closed-loop AC pilots remain separate, require independent post-run audit, and must not be conflated with the offline case solve.

## Qualification sequence
Verify read-only exact 508-source; Install single solver file plus two additions; Qualify test contracts and real Gurobi per MF01/MF02; run MF01 24-step pilot; independently audit; then MF02 24-step pilot; independently audit. Stop on failures, preserve original receipts and traces. No modifications to the frozen simulator, even in response to later failures, without separately approved general-purpose change.
