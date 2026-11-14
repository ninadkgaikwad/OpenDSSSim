# OpenDSSSim standalone IEEE-123 examples (01-10)

These **three direct Python scripts** replace the abstraction-heavy course style for the first learning stage. Read each file from top to bottom. All important settings are near the top, and every script has numbered sections. There is no `run_course.py`, no `course_utils`, and no controller algorithm.

**Recommended tutorials:** The numbered scripts directly inside `examples/` (01-10) are the current entry point. They are standalone, extensively commented examples, with `Input/` and optional `Output/` folders. There is no required `run_course.py` layer. **Native runtime validation is still pending** for the new tutorials.

The older [`ieee123_course/`](ieee123_course/README.md) is **under construction**, preserved as development/reference material, and **not recommended for new users**. Reinforcement-learning (RL) controller integration is **planned**, not provided as a finished tutorial in this release.

## What these examples teach

| Script | Purpose | Physical input changes? | Requires AltDSS? |
|---|---|---|---|
| `01_IEEE123_Environment_Basics.py` | Construct `OpenDSSSimulator`, reset, inspect public services, call `step({})`, save history and diagnostics | No — repeated snapshots at fixed feeder input | Yes |
| `02_IEEE123_TimeSeries_NoController.py` | Bind a synthetic hourly load CSV through `ReplaySource`, `ReplayBinding`, and `ReplaySpec`, run 24 steps, print and optionally save hourly results | **Yes** — all 91 IEEE-123 loads are scaled hourly | Yes |
| `03_Inspect_Saved_Results.py` | Read the resulting CSV, print statistics, optionally plot | No simulation | No — only CSV (and matplotlib if plotting) |

**No `ProblemSpec` means that the Gymnasium action space is `Dict({})`, and `env.step({})` is the appropriate call.** The Gym observation contains only `converged` by default. Detailed electrical summaries are available through `info["solution"]`, `env.last_result`, and the **read-only** `env.native_diagnostics()` service. Engine, circuit, inventory and semantic registries are also accessible directly. This is *not* an excuse to access `env._plant` or mutate AltDSS.

**No external controller does not disable the circuit's native OpenDSS `RegControl` and capacitor logic.** They remain in the feeder and can affect solutions. The examples intentionally do not alter them.

## Inputs and outputs

```text
examples/
├── 01_IEEE123_Environment_Basics.py
├── 02_IEEE123_TimeSeries_NoController.py
├── 03_Inspect_Saved_Results.py
├── Input/
│   ├── IEEE123_Base/                  # Original feeder DSS input files; do not edit
│   ├── ieee123_load_targets.csv       # 91 explicit Load.* identities
│   └── synthetic_hourly_load_multiplier.csv  # 24 hourly samples, synthetic
└── Output/
    ├── .gitignore
    └── <RUN_NAME>/                    # Created only if SAVE_RESULTS=True
        ├── hourly_results.csv
        ├── history.json
        ├── last_native_diagnostics.json
        ├── native_diagnostics_per_step.json
        ├── run_settings.json
        ├── Inventory/
        ├── SemanticRegistry/
        └── power_timeseries.png       # Optional, from script 03
```

All original feeder files are copied unchanged from the previous standalone prototype. The demand profile is **illustrative synthetic data** (not measured IEEE-123 demand). `ieee123_load_targets.csv` was derived from the 91 `New Load.*` definitions in `IEEE123Loads.DSS`; readers can deliberately select fewer loads to learn explicit physical bindings.

The output directory is not used as an input source. Each run has a separate `RUN_NAME`. If a name already exists, the scripts fail instead of overwriting results. With `SAVE_RESULTS=False`, temporary native inventory/registry metadata is discarded on exit.

## Install and run (later, in an environment with AltDSS)

From a Python environment with this exact OpenDSSSim repository installed (`pip install -e .`) and the AltDSS backend available:

```powershell
python examples/01_IEEE123_Environment_Basics.py
python examples/02_IEEE123_TimeSeries_NoController.py
python examples/03_Inspect_Saved_Results.py
```

If matplotlib is not installed, set `SAVE_FIGURE=False` in script 03 to print statistics without plotting.

## The essential time-series distinction

- `EpisodeSpec` changes the **logical clock**. With no time-varying `exogenous` or `exogenous_replay`, repeating `step({})` does **not** produce a changing demand profile.
- `ReplaySource` reads the timestamped CSV; `ReplayBinding` explicitly maps the demand multiplier column to physical `Load.*` objects; `ReplaySpec` validates timestamps, data coverage, and playback mode. The simulator applies this physical data before the native AC solve.
- In current A05 replay semantics, `reset()` solves input sample 0, and `step({})` #1 also solves sample 0. Step #2 uses sample 1, ... step #24 uses sample 23. Thus the 24-step loop executes **25 AC snapshots including reset** but represents 24 unique physical input hours. The `replay_sample_index` column makes this observable.
- `total_power_kw` is the signed circuit total-power value returned by the simulator, not a user-computed sum of nominal loads; `losses_kw` comes from the opt-in native diagnostic result. Do not assume it is metered energy.
- The default Gym observation is intentionally minimal. Later controlled lessons will teach richer observation and action spaces via `ProblemSpec`.

## Status

**Authoring/offline checks only.** These scripts have **not** been executed with the native AltDSS backend in this release. No simulator, controller, feeder, or semantic source code has been changed. We will approve the presentation and contracts before any native qualification.


---

## Examples 04-06: understand the public control contract before RBC or MPC

These scripts are standalone, deliberately explicit, and reuse OpenDSSSim's
existing `ProblemSpec`, `SemanticQuery`, `OpenDSSSimulator`, `ReplaySpec`, and
`ControllerContext` APIs. They do not modify `src/opendsssim/`.

| Script | Main lesson | External actuation | Input feeder |
|---|---|---|---|
| `04_IEEE123_ProblemSpec_Observations.py` | `ProblemSpec`, semantic selection, Gym observations and bus voltages | None | `Input/IEEE123_Base` |
| `05_IEEE123_ProblemSpec_Actions.py` | One PV Q action, action bounds/authority, requested/applied/realized readback | One 0-kvar PV command | `Input/IEEE123_P1` |
| `06_IEEE123_Controller_Context_Forecasts.py` | `ReplaySpec`, decision-time `ControllerContext`, forecast coverage, feedback | One 0-kvar PV command | `Input/IEEE123_P1` |

Each script has a preamble, numbered sections, explicit `SAVE_RESULTS` and
`RUN_NAME` settings, a visible `env.reset()` and `env.step()` loop, console
information, and optional output saved only under its own `Output/<run>/` folder.
With `SAVE_RESULTS=False`, persistence uses a temporary location. Existing
output folders are never overwritten.

From your installed repository root, after `pip install -e .` in a compatible
Conda environment (requires the installed AltDSS backend):

```powershell
python examples/04_IEEE123_ProblemSpec_Observations.py
python examples/05_IEEE123_ProblemSpec_Actions.py
python examples/06_IEEE123_Controller_Context_Forecasts.py
```

Review the `USER SETTINGS` section near the top of each script before running.
For repeated runs, change `RUN_NAME` or set `SAVE_RESULTS=False`.

### Important distinctions

- `ProblemSpec` is authored before constructing the simulator, then resolved
  against the feeder's semantic registry; it does not invent new native equipment.
- A `SelectionGroup.group_id` organizes authored selections; Gym observations
  are nested by `current / native class / object name / quantity`.
- An observation-only `ProblemSpec` has no external actions; `env.step({})`
  remains valid.
- An action contract with one PV reactive-power channel requires that complete
  channel in the action dictionary on **every** step. Examples 05/06 are not RBC.
- `ControllerContext` is read-only and detached. `forecast` covers selected
  physical exogenous inputs, not undisclosed future electrical truth.
- The examples have been reviewed statically but **not** yet native-run on a
  Windows/AltDSS system. Do not interpret them as independently qualified
  power-system experiment results.

## Examples 07-10: existing controllers in direct closed-loop steps

These four standalone scripts extend Examples 04-06 (which taught `ProblemSpec`
and `ControllerContext`). Each uses a **detailed preamble, numbered sections,
editable constants near the top, a thin `controller(state, forecasts)` function,
and a plainly visible `for` loop that calls `env.step(action)`**.

| Example | Controller | Primary lesson |
|---|---|---|
| `07_IEEE123_P1_RBC.py` | Installed P1 rule-based controller | PV Q droop, capacitor hysteresis, regulator taps; `on_success()` feedback |
| `08_IEEE123_P1_MPC.py` | Installed P1 horizon-12 MIQP | Public current state and forecasts → case update → Gurobi solve → first action |
| `09_IEEE123_P2_RBC.py` | P2 graph controller + original S10D-selected route | Structural preview **is not** electrical clearance; fault-aware route replay with AC/readbacks |
| `10_IEEE123_P2_MPC.py` | Installed P2 horizon-2 MILP | Original slack-first vs separately labeled service-first objective priority sensitivity |

### Setup and execution

From repository root, install the normal project environment and the
solver dependency (Gurobi only for Examples 08/10); do not run these as part of
a GitHub CI without a licensed solver and native AltDSS backend.

```powershell
python examples/07_IEEE123_P1_RBC.py
python examples/08_IEEE123_P1_MPC.py
python examples/09_IEEE123_P2_RBC.py
python examples/10_IEEE123_P2_MPC.py
```

**Settings:** Change `STEPS` (default 3, maximum 24) and `RUN_NAME` near the
top. Set `SAVE_RESULTS = False` to print and simulate without retaining output.
For P2 select `SCENARIO = "MF01"` or `"MF02"`; for MPC choose
`POLICY = "slack-first"` or `"service-first"`. Give each run its own name,
as scripts deliberately refuse to overwrite old results.

**Inputs:** `Input/IEEE123_P1/`, `Input/IEEE123_P2_MF01/`,
`Input/IEEE123_P2_MF02/`, `Input/ControllerCases/`, and
`Input/ieee123_load_targets.csv`. Cases and routes carry provenance in
`Input/ControllerCases/README.md`. No inputs are written during simulation.

**Outputs:** `Output/<RUN_NAME>/` holds per-step CSV results, action audits,
controller/optimization provenance, episode history, inventory, semantic
registry and preflight receipts. With `SAVE_RESULTS=False` temporary
preflight files are cleaned up and no permanent output is retained.

**Comparability:** P2 RBC is a 24-step continuation of S10D electrically
screened routes, **not fresh hourly RBC electrical optimization**. MPC performs
new horizon-2 optimization each step. P1 educational RBC monitor wiring and
P1 MPC are different control settings from the original archival S10C study;
use the qualified PESGM results archive for publication-reproducibility claims.
P2 nominal connected demand is a topology proxy. Thermal security is not
certified. The provided replay is synthetic constant hourly demand; it is not
realistic load/irradiance forecasting.

**Qualification:** Scripts 07-10 are statically/offline tested only at patch
creation. A native AltDSS/Gurobi smoke test is required before claiming the
lesson runs are fully scientifically qualified. The simulator and original
controller implementation have not been changed.

## Current tutorial status and future RL integration

**Examples 01-10 are the supported documentation path, not yet native-qualified**; all were checked offline and added to the repository through guarded example-only patches. They teach the installed public interface without changing the AltDSS plant or controller mathematics. Run the native examples in your own configured environment before relying on their outputs.

**RL controller integration is planned (coming up).** OpenDSSSim's existing `ProblemSpec`, action/observation layouts and decision-time `ControllerContext` will be the same interfaces used for RL. A qualified RL teaching example or trained agent is **not yet distributed** as part of these 10 scripts.

**Old course:** `examples/ieee123_course/` is retained for development reference but remains **under construction / not recommended**. Avoid starting with its extra `run_course.py` orchestration; begin with `01_IEEE123_Environment_Basics.py` instead.
