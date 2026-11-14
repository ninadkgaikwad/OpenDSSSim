# ControllerCases inputs (Examples 07-10)

These are explicitly qualified *offline static* multiphase LinDistFlow cases from
`examples/ieee123_course/input/mpc_baseline/cases/`, copied byte-for-byte,
including the original `CASE_PINS.json`. No model data is guessed or fitted here.

- P1 Volt/VAR: `ieee123_pesgm2027_lindist_case.json` and the original
  10-PV native irradiance discovery metadata. Horizon 12.
- P2 restoration: `ieee123_p2_mf01_simple_lindist_case.json` and
  `ieee123_p2_mf02_exotic_lindist_case.json`. Horizon 2. Original objective
  uses slack-first priority; the separate service-first solver has ONLY two
  lexicographic objective-priority values changed.
- `RBC_S10D_P2_Results_QUALIFIED.zip`: byte-exact archived native electrical
  screening of `MF01_RATIFIED_PARTIAL` and `MF02_ROUTE_A`. Use only as
  selected-route continuation, NOT a fresh electrical evaluator.
- `constant_hourly_load_multiplier.csv`: newly authored **synthetic** 48-hour
  hourly load multiplier 1.0 for all 91 loads. It does NOT represent actual
  observed demand, real weather, historical load, or PV production. It gives
  sufficient declared replay horizon for 24 MPC decisions plus horizon 12.

**Solver provenance:** `p2_service_first_sensitivity_solver.py` is an *example-
side* copy of the installed R02 P2 solver, with EXACTLY two objective priority
integer changes. `10_IEEE123_P2_MPC.py` compares its full bytes to the
expected two-edits-only transform of the installed solver and aborts on drift.
No `src/opendsssim/` file is modified or monkeypatched at runtime.

The physical replay sampling interval is 1 hour. The P2 optimization objective
uses a separate 0.25-hour `dt_hours` model parameter. Do not interpret the
objective's weighted unserved kWh as measured 24-hour delivered AC energy.
All network geometry/topology and action semantics stay within OpenDSSSim's
published `ProblemSpec` and `ControllerContext` interfaces.
