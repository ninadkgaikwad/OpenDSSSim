# MPC A02 — P1/P2 Gurobi optimization engines (source-first qualification)

**Status:** MPC optimization source implementation; **NOT** native closed-loop or PESGM numerical science qualification.

## Authority, source and scope

This additive A02 package is based **only** on the independently verified MPC A01
333-file source ZIP, SHA-256 `E66CA2D372BABC027181CBB0B4E3A0D0F8D7E5F477CEE4885C326A9A532AB950`,
and A00 tree manifest SHA-256 `7E29CF4C37B6D1BE0ABB214935A2FBA3240368908775EACC64814E725E272192`.

The scientific authority is `P1_VoltVAR_DER_ControlScience_FROZEN.tex`,
`P1_Optimization_Controller.md`, and
`P2_Reconfiguration_Restoration_ControlScience_FROZEN.tex` Block 7.
Do not implement P2 from the older `P2_restoration/P2_Optimization_Controller.md` scaffold.
No existing simulator, Plant, feeder, RBC, or published action semantics change.

## Installed module roles

- `contracts.py`: explicit typed multiphase network, forecast, load, physical-device
  and thermal-rating contracts, with strict finite-value/dimension checks.
- `p1_miqp.py`: horizon MIQP, phase coupling via R/X matrices, squared bus-phase
  voltages, PV apparent-headroom bounds, binary capacitor states, integer
  bounded tap moves, voltage slack, and weights `w_V/w_sw/w_Q`.
- `p2_milp.py`: horizon MILP, hard health constraints, coupled source connectivity
  and radiality using directed fictitious flows, bus/phase power balance,
  phase-aware voltage-drop matrix, eight-sided thermal polygons when ratings
  supplied, curtailable load service, hard mandatory service at energized buses,
  and lexicographic Gurobi objectives (operational slack, weighted unserved
  energy, switching count). The controller model is SINGLE UTILITY SOURCE.
- `actions.py`: complete first-step conversion through the existing A04 encoder
  and current `controller_context()`; no direct DSS action or native handles.

## Critical scientific requirements before a real native experiment

Neither `controller_context()` nor the current static inventory contains
validated per-line/phase impedance matrices, regulator linearization
coefficients, and all requested P2 thermal ratings. The explicit model objects
**must** be constructed by a separate read-only static-circuit model compiler
whose topology and electrical units are independently qualified. No arbitrary
coefficients should be used for actual IEEE-123 results. In particular:

1. P1 needs an oriented, phase-connected radial tree; `r/x` must be **squared
   per-unit voltage drop per kW/kvar** after physical unit conversion.
   Device-to-phase allocation, PV availability, capacitor kvar and actual tap
   metadata must be verified against real circuit files and current A04 state.
2. P2 requires phase-aware source and load incidence, healthy branches,
   current switch readback, fault masks, and actual phase matrices. Phase-disjoint
   parallel regulators need corridor normalization (as S10D RBC established),
   but genuine parallel loops must stay distinguishable.
3. P2 default behavior **fails closed** for missing thermal ratings. An explicit
   `voltage_only_exploratory=True` switch allows a labeled exploratory case
   without falsely claiming a thermal certificate. Equal load priorities or
   empty curtailment eligibility must be labeled as experimental assumptions.
4. Production P1 horizon: 12 steps of 5 min (fixed in P1 science). P2 time
   step and horizon must be declared in experiment configuration. No use of
   future realized exogenous observations. A genuinely dynamic horizon requires
   qualified forecasts/updates, not static candidate screens.
5. Gurobi solve status, incumbent optimality, model residual/constraint audit,
   A04 action audits, and nonlinear native power-flow readback are separate.

**A02 is not permission to claim that MPC P1/P2 has beaten RBC.** Real native
MPC campaigns, computed feeder-specific model coefficients and stored matched
comparisons belong to the subsequent qualification work.

## Reproducibility and known reliability notes

Install is guarded by all 333 predecessor file hashes, the current A00 tree
and A01 directed-source evidence; old installed source is never overwritten.
Qualification requires real `gurobipy`, not a fake optimizer or silent skip.
R01 remains OPEN; R02 OPEN_MITIGATION_QUALIFIED. Full regressions must retain
native exception evidence, with no interpretation as fixed physical delay.
