# B00 — Native-Controls Time-Series Baseline: Design and Qualification Contract

**Status:** Proposed first controller-science implementation, not yet coded or natively qualified.  
**Scope:** generalized reference runner and adapter with no external supervisory actions. Preserve A05I6R2 source freeze and the installed IEEE-123 feeder definitions.

## 1. Precise baseline definition

**B00 / NATIVE-AS-INSTALLED:** external exogenous profiles advance through the qualified A05 physical time-series pipeline, the native OpenDSS controls *already defined in the feeder* remain under native authority, and no outside RBC/MPC/RL supervisor issues commands. Each controller epoch calls the existing simulator once via `env.step({})` (provided the compiled ProblemSpec has an empty action Dict), not an independent AltDSS solve.

This is **quasi-static time-series** (successive native Snapshot solves with an external clock), not a claim that OpenDSS daily/yearly time mode, time-delay semantics or control-queue replay have been validated. Native control behavior, `ControlMode`, tap changes and control iteration counts must be measured on the laptop before declaring the B00 implementation qualified.

**Current exact feeder facts established by inspected source**:

| Feeder | Load objects | RegControl | Capacitors | PVSystem | CapControl | InvControl |
|---|---:|---:|---:|---:|---:|---:|
| `experiments/pesgm2027/feeders/ieee123_base/IEEE123Master.dss` | 91 | 7 | 4 | 0 | no objects defined | no objects defined |
| `experiments/pesgm2027/feeders/ieee123_pesgm2027/IEEE123Master.dss` | 91 | 7 | 4 | 10 | no objects defined | no objects defined |

Here, **capacitors are static banks**, not native `CapControl`-operated banks. The working feeder's ten PV systems have initial `kvar=0` and no native `InvControl` Volt/VAR curve. Never report this B00 run as controlling PV VARs or switched capacitor banks automatically.

**Do not silently import settings from `Run_IEEE123Bus.DSS`.** Its optional `RegControl.Maxtapchange`, delay and `Set MaxControlIter=30` commands belong to that alternative run script; the simulator loads the actual `IEEE123Master.dss` directly. Verify loaded control settings from native inventory; if alternate native-control parameterization is desired, define a separately versioned scenario/overlay, not a source feeder overwrite.

## 2. Ownership and signal flow

```text
physical CSV/Parquet truth -> A05I3 replay -> A05I2 physical writer
                                             |
                                      native Plant Snapshot solve
                                             |
                     existing native RegControls (if enabled)
                                             |
                              A04 observation / A05 history / metrics
                                             |
                    B00 no-op supervisor -> env.step({}) for next epoch
```

No outside access to `env._plant`, AltDSS contexts, native direct setters, or physical mutation. Where a measurement is required, bind it through declared A03/A04 semantic state/observation and recorder; missing metrics must cause an explicit capability-gap result, not an invented value.

A03/A04 **native authority** is retained for the relevant regulator controls; no external action binding is selected for B00. A native auto-control device whose `Enabled` or ControlMode is disabled must not be presented as operating without evidence. `ProblemSpec` can select a rich observation while its action layout stays empty; verify empty-action-space behavior in native integration tests.

## 3. Experiment cases and fair-comparison contract

**B00.1 Canonical IEEE-123:** time-varying load P/Q, seven existing regulators; four fixed capacitor banks, no DER.  
**B00.2 PESGM2027 IEEE-123:** same measurement and load schedule (where device mapping allows), ten PV irradiance/temperature trajectories, existing regulators, four fixed capacitors, PV reactive commands remain at scenario-defined fixed values.  
**B00.3 Negative control:** native controls explicitly inactive only in a *separate, declared scenario* for ablation—do not alter the canonical/working feeder by default.

B00 and P1 controllers must share initial tap/cap states, source hashes, feeder revision, replay timestamps, PV truth, load trajectories, fault assumptions, control interval, convergence and metric definitions. Forecast access must be explicitly declared; B00 need not call the A05 oracle or Gaussian forecast merely because these services exist.

## 4. Proposed generalized code boundaries (not installed yet)

- `src/opendsssim/controllers/baselines/native_controls.py`: reusable, capability-checked **no-supervisor-action adapter**. This is orchestration logic only; it does **not** implement another electrical simulator or override native regulators.
- `configs/controllers/native_controls/`: native B00 configuration and typed runtime expectations, including which object classes are present/active and which are absent.
- `experiments/pesgm2027/`: paper-specific feeder selection, profiles, seeds, episode lengths and reporting campaigns; no IEEE-123 IDs hard-coded in generalized controller implementation.
- Reuse the frozen `OpenDSSSimulator(..., problem=..., exogenous_replay=...)`, `reset()`, `controller_context()`, `step({})`, and `history`. If any needed metrics or control-mode readbacks are missing, create an explicit service gap and independently qualify an extension rather than reaching into the backend from controller code.

## 5. Native qualification gates (all required)

1. **Qualified predecessor:** verify the exact 243-file A05I6R2 runtime source identity (or the 245-file docs-only successor), and no unrelated P2/unmanifested-file mutation.
2. **Feeder discovery:** both master files load; native control inventory accurately reports seven RegControls and absence of CapControl/InvControl; capacitors and PV counts as above.
3. **Control availability:** record and verify native `RegControl.Enabled`, effective control mode, regulator settings, control-queue/tap-change behavior, and any `ControlIterations`; do not infer automatic operation solely from file declarations.
4. **Time-series physics:** verify one reset solve + N step solves for N completed epochs; all actuals applied at the intended clock index; no extra external solves; strict/tile replay and provenance survive.
5. **No external actions:** exact empty A04 Dict action; `env.step({})` only; `a_requested`, `a_applied`, and `a_realized` audits remain consistent, and no direct controller-native mutations occur.
6. **Measurements and outcomes:** per-epoch convergence, bus/phase voltage extrema and violations, feeder P/Q and losses (if exposed by qualified semantics), regulator tap positions and changes, capacitor states, PV P/Q where present, control iterations, total solver calls, and profile provenance. Metrics that are not yet exposed are marked `NOT_IMPLEMENTED`, never fabricated.
7. **Repeatability:** fixed feeder/profiles/configuration gives equivalent deterministic electrical results within declared tolerances; fresh-context reset starts from the same baseline; both feeders are tested for full multi-step episodes.
8. **Regression:** qualified A05 targeted and full tests remain passing; R01/R02 observations are captured and reported, not hidden.

**Acceptance artifact:** B00 native results ZIP with exact source/config/profile fingerprints, per-step metrics, control-state trajectories, comparison table, test logs, and independent audit receipt. **Do not claim B00 implemented or accepted until that evidence is reviewed.**

## 6. Later extensions, not B00

- Native `CapControl` and native `InvControl` / Volt-VAR are not present in the current two feeder masters. If useful, a **B01 native-automation variant** may install those objects through a separately versioned, reversible scenario overlay without changing the canonical working feeder; it needs its own authority, control-mode and baseline-parity qualification.
- P1 RBC, MPC, and SB3 Branching Dueling DDQN use the same A04/A05 interfaces with externally authorized PV Q/capacitor/regulator actions as required by their frozen science contracts.
- P2 switching MPC/RL remains a separate experiment and does not authorize exogenous outages or repair events under A05 V1.
