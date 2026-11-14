# OpenDSSSim: first examples — no ProblemSpec, no external controller

These **three direct Python scripts** replace the abstraction-heavy course style for the first learning stage. Read each file from top to bottom. All important settings are near the top, and every script has numbered sections. There is no `run_course.py`, no `course_utils`, and no controller algorithm.

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
