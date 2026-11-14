# RBC S09A — Controller-only implementation (IEEE-123 P1/P2)

**Science provenance:** `P1_Reference_Controller.md`, `P1_VoltVAR_DER_ControlScience_FROZEN.tex`, and the **final** P2 `P2_Reconfiguration_Restoration_ControlScience_FROZEN.tex` (Block 6) plus ratified MF01/MF02 design. The older `P2_restoration/P2_Reference_Controller.md` is a nonfrozen scaffold and is not implementation authority.

**Source predecessor:** Qualified S06RF successor, 324 files, manifest SHA256 `07CD5069685165016A0AE319EBEFA2A0126ED25A69717229417BF5A8168310A2`; fresh S07 tree SHA256 `98706B08F59828BFC56D748BCFE6C9D2CD5E268E941BEBBEC1722E68F8A73E33`; fresh S08 directed manifest SHA256 `65A549763A6F3D6C407C8228535F9BCEE04A41B54BA5406D73331FB24465E32F`.

## Exact scope and honest qualification boundary

New files exist **only** under `src/opendsssim/controllers/reference/`, new unit/integration tests, and this documentation. None of A03/A04/A05/B00, A02, AltDSS, the Plant, feeder masters or historical P2 assets is edited. The controllers use `ControllerContext`, A04 `ProblemSpec`, and `env.step(a_req)` as sole physical action boundary; they never import native backend methods, bypass authority, or call another solver.

### P1 implementation

- `make_p1_problem` creates a fixed A04 external-authority action set for every explicitly configured PV, capacitor, and transformer; it selects bus voltages and realized capacitor/tap states. A04 owns native RegControl suppression.
- `P1RuleBasedController.decide(context,pv_available_kw=current_values)` computes the same-observation vector: configurable monitor reductions (IEEE multphase `AVG`), frozen piecewise PV Volt/VAR with `sqrt(kVA^2-P_available^2)`, cap ON <=0.97/OFF >=1.03/otherwise realized hold, and regulator ±1 semantic tap steps outside 1.0 +/-0.0125. It converts requested steps into absolute native transformer ratio, clamps to A04 bounds, and emits the **entire** action dictionary; no delayed actuation.
- Per-device monitor bus/index, inverter rating, available *current-time* PV active power, transformer winding and physical tap ratio step must come from validated experiment configuration/telemetry, not controller inference. A missing datum raises `ControllerContractError`. There is no future information leakage or guessed PV `P_available`.
- Successful-action memory updates only after A04 reports converged, admissibly applied action. Both controllers provide an explicit `fallback()` method to return the last *successful* command only within the same episode, accompanied by a separate fallback-event reason; callers must still send it through A04 validation and must record the event. If no successful command exists, fallback fails closed.

### P2 implementation

- `make_p2_problem` declares exact switch and curtailable-load actions and fixed multi-fault health masks using A04 `FaultSpec`. No direct Load.kW/kvar disturbance writes.
- `P2GraphController.preview` reads only the authorized detached static network and current switch/load observations; enumerates complete switch vectors, rejects health-down edges and energized graph cycles, computes source-connected load priority-weighted nominal restoration and switching effort. It **emits no action** and is explicitly labeled `STRUCTURAL_ONLY_NOT_ELECTRICALLY_QUALIFIED`.
- `P2GraphController.decide` requires a separately qualified, current-state, **nonmutating** controller-side electrical evaluator. It will not emit an action without that evaluator. Within the evaluator interface it implements priority-first curtailable-load reduction, bounded bisection for minimum necessary reduction under an evaluator-checked monotonicity assumption, score ranking, and full-vector action encoding. This is an algorithm implementation, not a claim of a validated LinDistFlow evaluator.
- Graph check is bus-level radiality; it does **not** establish unbalanced phase-level or actual voltage/thermal feasibility. Any final P2 closed-loop physical claims require a qualified phase-aware electrical evaluator and explicitly declared real line ratings, priority assignments and curtailability. The ratified design leaves these quantities unresolved; we will not fabricate them.
- Fixed-but-unavailable loads have no controller action: unserved status is determined via source connectivity and physical solve. Reported structural nominal connectivity is **not** delivered kW.

## External experiment wiring

Instantiate `OpenDSSSimulator(network,problem=make_p1_problem(...))` and obtain `ctx=env.controller_context()` after reset. Construct explicit `P1Spec` monitor/winding/availability mappings from permitted current data; `action, diagnostics=policy.decide(ctx,pv_available_kw=current_pv)`, then make exactly one `env.step(action)`. For P2, provide static load bus and priorities plus a qualified electrical evaluator, call `decide` and only call `env.step(decision.action)` when `decision.action` is not None. `preview` returns a structural-only report and MUST NOT be applied physically as a certified RBC decision.

## Evidence and next boundary

This first S09A additive installation supplies actual P1/P2 algorithm code, pure unit tests, and native public contract compile/reset tests. Windows native tests, repeated regressions and source hashes are part of S09A qualification but are **not** P2 restoration closed-loop qualification. Completing the frozen science study additionally requires controller-side multiphase LinDistFlow qualification, explicit validated priority/curtailability and operational limits, repeated P1/P2 closed-loop datasets, recorder-backed comparisons and independent audit. Any subsequent source patch must repeat fresh tree -> fresh directed-source collection.

R01 Windows native exception traces remain OPEN. R02 capacitor JSON mitigation remains OPEN_MITIGATION_QUALIFIED. B00's 24-hour series remains synthetic diagnostic data and does not validate physical control delays.
