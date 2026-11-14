# S06 — OpenDSSSim general controller-capability extension

**Status:** Approved design; installation and native qualification are separate pending gates.  
**Authorization:** User approved a controller-agnostic simulator improvement on November 9, 2026 after S03 native capability probing.  
**Predecessor:** Frozen B00 V1 266-file manifest SHA-256 `CE9B506030AD3319AC5D393F47FF69E29F6B35631B51B66F252A5D884D82C163`, plus 56 separately tracked P2 experimental files (manifest SHA-256 `4A83C0F1AA903B0C6A59127263AFFFCBDB1D838DA2F582316AE4F64F04A7E945`). All 322 source files are verified before any guarded S06 patch application.

## 1. Scope and authority

This is a **general OpenDSSSim semantic/native-access improvement**. It does not contain any P1, P2, RBC, MPC, RL, feeder-specific rule, switch plan, objective, weight, or controller optimizer. It must not edit DSS feeder files, electrical impedances, device inventories, frozen math, or the B00 comparison runner.

S06 introduces a new semantic-policy **identity**, explicitly superseding (not rewriting or silently reusing) the frozen A03 V1 policy. The original B00 manifest is retained as historical evidence; an installed, approved S06 improvement creates its own successor manifest. All changes must be independently reviewed for native regressions.

## 2. Typed native-state observations

| Device / semantic quantity | A03-native address | Native source of fixed shape | Gym encoding |
|---|---|---|---|
| `capacitor_state` | `Capacitor.States` | Length of native States property array, read during semantic compilation | Fixed-length numeric Box |
| `transformer_tap_position` | `Transformer/AutoTrans.taps` | Length of native Taps array, read during semantic compilation | Fixed-length numeric Box |
| `branch_open_state` | `CircuitElement.open_state` | `CircuitInventory.elements[].num_terminals`, matching native `IsOpen(terminal, 0)` | Fixed-length MultiBinary |

Only static array **shapes**, not initial guesses or hard-coded feeder cardinalities, are captured. Actual state values still come from native readbacks after each solve. Missing or malformed shape evidence fails closed. All channel selection and authorization remains with `ProblemSpec` and A04. No native handle is exposed to controllers.

## 3. Load-service fraction: general physical action

`Load.kW` and `Load.kvar` remain `STEP_EXOGENOUS` physical demand channels. They are **not** reclassified as actions. A separate `RuntimeCommandAddress(service="Load", operation="set_served_fraction", entity="Load.<name>")` yields semantic action `load_service_fraction`, a continuous scalar bounded intrinsically by `[0,1]`.

At an authorized step, A05 writes the current physical uncurtailed kW/kvar truth, if an exogenous source is bound. A04 validates the requested fraction and ownership, then invokes the one backend service command. The command scales both native kW and kvar by the same fraction: `P_native_setpoint=alpha*P_available`, `Q_native_setpoint=alpha*Q_available`, preserving power-factor sign as defined by the source. A **single authoritative AltDSS snapshot** follows, then the action is checked via native kW/kvar readback and a nominal applied setpoint fraction. It does not silently invoke a second solver.

An owned-backend per-load *uncurtailed* P/Q baseline avoids accumulating curtailment across steps without new exogenous samples. A05 native load-property writes update that baseline and reset the intermediate fraction to 1 until the next accepted action. The cache is cleared on circuit reload/reset, and never shared across backend contexts.

Read-only state channels are:
- `load_available_active_demand_kw` (pre-service P demand);
- `load_available_reactive_demand_kvar` (pre-service Q demand);
- `load_service_applied_fraction` (native **P/Q setpoint ratio**, not a claim that a disconnected/islanded load is electrically served).

These are distinct from A03 `load_active_power_demand` / `load_reactive_power_demand` native-property readouts, which reflect the current **post-action** kW/kvar values if service was adjusted. Controller requirements for pre-curtailment demand must explicitly select the new available-demand state channels. The A05 provenance receipt continues to identify independently applied exogenous source P/Q, without a second, controller-owned disturbance writer.

The service exposes no load-priority, network-flow, fault, topology, radiality or optimization logic; all of that is a controller/problem configuration responsibility. Native write/readback mismatch is an explicit error requiring reset. A04 fault lockout rejects actions against `FaultSpec` targets; current A04 may report an initially disabled device as unavailable through controller context without rejecting its nominal setpoint write. A controller must not interpret a successful nominal Load.kW/kvar write as proof of electrical energization or actual delivered power; measure the native solved electrical response separately.

## 4. Deferred and prohibited

- **PV telemetry:** no new PV-channel assumption is installed in S06. The available PV irradiance driver and static Pmpp/kVA values already exist; availability versus realized power must be qualified separately before expanding telemetry. It must not be inferred from the wrong sign convention or invented data.
- **No regulator/switch ownership bypass.** Existing native control suppression and A04 authority remain responsible.
- **No enforcement of P2 radiality or network constraints by Plant.** Structural graph search and candidate evaluation remain controller-owned. Feeder ampacity limitations are not fabricated.
- **No automatic curtailment priority assignment.** A controller must provide the authorized selected loads and actual fractions.

## 5. Minimum native qualification

1. Exact 322-file predecessor and historical B00/P2 hashes verified before installation; only explicitly allowlisted source files change; full successor manifest and backups in Downloads.
2. Native compile/reset of per-capacitor/per-tap/per-switch observations on real P1, MF01 and MF02 feeder masters.
3. Native fixture test of service `alpha=0.5 -> 0.5 -> 1` to prove no compounding; check P/Q readback and physical convergence.
4. A05 time-varying P/Q native demand test with `alpha=0.5` and `0.25` and no co-ownership or demand-provenance corruption.
5. Native invalid-action rejection, reset restoration, A04 action audit and controller context readback; confirm one authoritative solve per step.
6. B00 integration and four-feeder comparison tests; three complete full-suite regressions; explicitly report R01/R02 native reliability traces.
7. Source invariance check of every unmodified predecessor and all 56 separate P2 files, with external independent evidence review.

A package installer PASS does **not** constitute scientific or native qualification. On qualification failure, do not reinstall or roll back; collect a new fresh tree, fresh directed source, and independent evidence before a repair.
