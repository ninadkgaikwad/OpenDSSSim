# A07A2 OpenDSSSim native closed-loop MPC pilot

**Scope:** controller-side experimental integration for the ratified IEEE-123 P1 Volt/VAR and P2 MF01/MF02 restoration problems. Does not alter A03/A04/A05/B00 simulator, feeders, physics, Plant, backend, semantic registries, native control states, existing Gurobi solvers, or existing RBC code.

## Physical/control separation

* Offline network coefficients, static topology, current nominal load, device ratings and one PV reference are captured by the **qualified independent AltDSS A06R5R1** data archives, pinned in this package. This offline AltDSS context is **not** the live control plant and is **never** mutated by this controller.
* The live simulator is **OpenDSSSimulator**. Its `ProblemSpec` is authored with the existing source-approved `make_p1_problem` or `make_p2_problem`. `reset()` creates the authoritative AC snapshot, `controller_context(forecast_horizon=H, required=False)` provides **selected** live state and eligible future exogenous profiles, and `env.step(action)` alone applies an authorized action and performs the next nonlinear AC solve.
* P1 uses multiphase 12-step LinDistFlow Gurobi MIQP; P2 uses two-step exploratory LinDistFlow MILP with explicit static faults and **no thermal security claim**. The Gurobi engines and pure A06 compiler remain **byte-identical**. The first action is encoded with the existing A04 reference action contract and only sent to `env.step` in the explicitly requested Pilot mode.
* Available declared replay signals: `load.multiplier` for load profiles and `pv.irradiance` for PV. P1 derives a **simplified** available-P forecast from the offline native reference `P_at_Iref` times authorized irradiance / static native reference irradiance. This does **not** assert measured current PV kW or calibrated temperature/equipment efficiency. If forecasts are unavailable, document and use the current observation for P2 or offline native snapshot persistence for P1; do not read future truth/private history. P1 load multiplier must be uniform to use the node-aggregated case; heterogeneous profiles fail closed.
* P1 capacitor C83 has three physical phases but one observed action bank. The optimized phase commands are collapsed to its single command only if **all phases agree**; an inconsistent decision fails closed, with no hidden projection and no `env.step`. Transformer taps are taken from authorized two-winding position readback and normalized to the static tap grid. P2 uses current switch readback; static fault masks override readback, without inventing healthy switches.

## Execution modes

* `Verify`: read-only full prepatch source/hash verification, 502 files; no Python imports.
* `Install`: exact four-file add-only patch after fresh A07A0/A07A1 evidence, strict 502→506 source verification; **never rerun Install** after success.
* `Qualify`: 15 isolated mathematical/contract tests plus three genuine OpenDSSSim `reset()` and `controller_context` inspection runs with **no Gurobi** and **no `env.step`**. Real native Windows AltDSS acceptance requires independent audit of the generated ZIPs.
* `Pilot`: one chosen feeder at a time; 1–24 bounded receding-horizon time steps, actual Gurobi optimization and `env.step`. Explicitly exploratory until independent qualification. Never claim verified thermal security, AC sensitivity calibration, field data, or closed-loop performance if any step fails.

The runner's default declared exogenous replay reuses the **existing** B00 physical-data construction with constant, synthetic 1-pu load multiplier and 1-kW/m² PV irradiance. It makes eligible forecast values available through the **official** OpenDSSSim forecast service. They are **not** measured demand or a field forecast. `-NoReplay` intentionally exercises the documented persistence fallback. The authority and identity of all delivered exogenous data belong to OpenDSSSim, not to the MPC.

**Known scientific limitation:** Existing frozen `solve_p1` / `solve_p2` result dataclasses expose first actions, solver summaries and (P2) energized buses but **do not export predicted bus-phase voltage trajectories**. This pilot therefore logs solver operational slack and actual AC bus voltages but marks predicted-versus-realized voltage trajectory error **not yet computable**, rather than inventing predictions. A later controller-agnostic or separately approved solver-result extension could expose those predictions.

All evidence, logs and episode results are written under Downloads; no outputs under the source repository. Fatal native import diagnostics observed in earlier pytest runs remain an open environment stability issue. Do not run parallel AltDSS processes, repeat native failures indiscriminately, or automatically retry after source installation.

## 24-step evaluation correction (pre-install candidate)

A07A2 is configured for **24 successive hourly OpenDSSSim `env.step()` calls** per feeder (full 24-hour exploratory episode). The **P1 mathematical prediction horizon remains H=12** and the **P2 mathematical prediction horizon remains H=2**; neither existing solver nor frozen math contract is changed. At each of the 24 steps, the driver re-solves with the then-current controller context and applies only the first control action through the official `ProblemSpec` action space and `env.step()`. Pilot default is 24, and the runner accepts `-Steps 1` through `-Steps 24`.

**Not a 24-hour variable-demand dataset:** the current default B00 replay is synthetic and constant (load multiplier 1 pu, PV irradiance 1 kW/m^2). Full 24-step success requires all steps to converge and may fail early on solver infeasibility, P1 capacitor-bank phase incompatibility, fault/action audit mismatch, or native backend errors. This corrected candidate is not real-native qualified merely by extending the loop bound. For paper experiments, use an independently qualified time-series replay and matching RBC/MPC conditions.

**Do not install the earlier 8-step A07A2 ZIP.** This corrected archive is based on the same independently audited, unchanged 502-file A07A0/A07A1 predecessor and contains the same four add-only payload paths. Keep the original source-evidence gates and do not modify any simulator or frozen solver source.
