# OpenDSSSim

**A generalized Gymnasium interface for electric distribution-system simulation and control, backed by AltDSS.**

OpenDSSSim separates a physical feeder and power-flow engine from its **problem declaration**, **semantic observations**, **authorized actions**, **time-series environment**, and **controller algorithms**. The objective is to make distribution-system control studies reproducible without embedding one control problem—or one controller—inside the simulator itself.

> **Research software / prerelease (`0.1.0a6`).** This repository is a teaching/research snapshot, not a certified utility operations platform. It is not suitable for safety-critical grid switching. The current tree contains a `LICENSE` file, but its approved scope, software attribution and third-party feeder permissions still require publication review; see [LICENSE_REVIEW_REQUIRED.md](LICENSE_REVIEW_REQUIRED.md).

## Start here: the supported standalone IEEE-123 examples

**The recommended learning path is now [`examples/`](examples/README.md), Scripts 01-10.** Each script is a standalone, extensively commented Python program with a preamble, numbered sections, editable input/output settings, and direct calls to the installed `OpenDSSSimulator` APIs. You do not need a separate tutorial runner or extra course abstraction to understand what the simulator does. The scripts make `env.reset()`, public information services, `env.step(action)`, and optional CSV/JSON output visible in the user code.

### Learning sequence

| Script | Topic | What you will practice |
|---|---|---|
| [`01`](examples/01_IEEE123_Environment_Basics.py) | Environment basics | Open an IEEE-123 feeder, reset, discover engine/circuit capabilities and diagnostics |
| [`02`](examples/02_IEEE123_TimeSeries_NoController.py) | Uncontrolled time series | Bind synthetic hourly load profiles with replay services, step through AC solutions, record results |
| [`03`](examples/03_Inspect_Saved_Results.py) | Inspect saved results | Read CSV/JSON, summarize results, optionally plot without re-running AltDSS |
| [`04`](examples/04_IEEE123_ProblemSpec_Observations.py) | `ProblemSpec` observations | Select semantic quantities, resolve the problem, and inspect Gymnasium observations |
| [`05`](examples/05_IEEE123_ProblemSpec_Actions.py) | `ProblemSpec` actions | Author actuator authority, encode a PV-Q command, inspect requested/applied/realized actions |
| [`06`](examples/06_IEEE123_Controller_Context_Forecasts.py) | Information and forecasts | Use read-only `ControllerContext`, decision-time exogenous forecasts, and feedback |
| [`07`](examples/07_IEEE123_P1_RBC.py) | P1 Volt/VAR RBC | Reuse the installed rule-based controller in an explicit AC closed-loop `for` loop |
| [`08`](examples/08_IEEE123_P1_MPC.py) | P1 Volt/VAR MPC | Reuse the qualified horizon-12 Gurobi MIQP, apply the first action, repeat |
| [`09`](examples/09_IEEE123_P2_RBC.py) | P2 restoration RBC | Study graph preview, fault locks, and continuation of previously screened switching routes |
| [`10`](examples/10_IEEE123_P2_MPC.py) | P2 restoration MPC | Reuse the horizon-2 MILP; compare original slack-first with the labeled service-first sensitivity |

For detailed annotations and the input/output folder guide, read the [standalone examples README](examples/README.md). The first three scripts do **not** require a `ProblemSpec` or an external controller. Scripts 04-06 introduce contracts before optimization, and 07-10 show the controller integrations without modifying the physical simulator.

### Quick installation and first runs

From this repository's **root directory** in a Python environment with AltDSS installed:

```powershell
conda create -n opendsssim-demo python=3.11 -y
conda activate opendsssim-demo
python -m pip install -e ".[dev]"

# Read/edit USER SETTINGS near the top of each script before running it.
python examples/01_IEEE123_Environment_Basics.py
python examples/02_IEEE123_TimeSeries_NoController.py
python examples/03_Inspect_Saved_Results.py

# Learn ProblemSpec and controller-visible information.
python examples/04_IEEE123_ProblemSpec_Observations.py
python examples/05_IEEE123_ProblemSpec_Actions.py
python examples/06_IEEE123_Controller_Context_Forecasts.py
```

The controller examples use the same direct script pattern. **MPC requires Gurobi (`gurobipy`) and an appropriate license**; the other scripts do not require Gurobi:

```powershell
# RBC examples
python examples/07_IEEE123_P1_RBC.py
python examples/09_IEEE123_P2_RBC.py

# MPC examples (install/configure licensed Gurobi first)
python -m pip install gurobipy
python examples/08_IEEE123_P1_MPC.py
python examples/10_IEEE123_P2_MPC.py
```

The scripts have settings such as `STEPS`, `RUN_NAME`, `SAVE_RESULTS`, and scenario/policy selections where applicable. They read pinned feeder and controller inputs from `examples/Input/` and optionally create isolated runs in `examples/Output/<RUN_NAME>/`. An existing output run directory is not overwritten. **These newly written examples have passed offline checks but have not yet been independently native-run end to end; treat the commands as usage instructions, not a claim of runtime qualification.**

### Development status and alternative tutorial

- **Current recommended examples:** `examples/01_...py` through `examples/10_...py` as listed above. Script source and input data are present; native tutorial validation is pending.
- **Reinforcement-learning controller integration:** **planned / coming up**, not yet provided as a qualified example. No RL example is promised as working in this release.
- **Legacy [`examples/ieee123_course/`](examples/ieee123_course/README.md): under construction.** This earlier 11-lesson course uses an additional `run_course.py` / `course_utils` layer. It remains in the repository for research/development reference but **is not the recommended entry point and is not considered sufficiently polished or runtime-qualified for new users**. Its earlier README/commands may not reflect the current preferred API-teaching approach.

### Other documentation

| Goal | Reference |
|---|---|
| Understand simulator architecture | [Architecture](docs/tutorial/02_ARCHITECTURE.md) |
| Develop `ProblemSpec` and public API integrations | [Public API](docs/tutorial/01_PUBLIC_API.md) |
| Integrate controllers without touching the plant | [Controller programming](docs/tutorial/03_CONTROLLER_PROGRAMMING.md) |
| Understand limitations and evidence standards | [Scientific limitations](docs/tutorial/04_SCIENTIFIC_LIMITS.md), [testing](docs/tutorial/05_TESTING_AND_REPRODUCIBILITY.md) |
| Cite the software and reproduce study conditions | [Citation](#how-to-cite-opendsssim), [reproducibility](docs/tutorial/06_CITATION_AND_REPRODUCIBILITY.md) |

## Features

- **Engine-independent control contracts.** Declare `ProblemSpec` observations, external action authority, device faults and other capabilities; the simulator validates them against feeder/semantic inventory.
- **Gymnasium `reset()` / `step()`.** Compiled `Dict` spaces and reproducible action/observation identities, with action application and realized-state audit records.
- **AltDSS physical backend.** Native AC snapshot solves and semantic inventory, not a controller-specific synthetic plant.
- **Time-series and forecasts.** Episode time, declared exogenous profiles/replay, current vs future information separation, forecast oracle/noise, and history levels.
- **Read-only controller context.** Detached observations, authorized device commandability, action layouts, source/network topology and feedback; **controllers cannot directly mutate AltDSS**.
- **P1 Volt/VAR + DER.** Ten additional PV inverters; the IEEE-123 regulators and capacitors remain original. RBC droop/hysteresis and MPC MIQP with 12-step horizon.
- **P2 restoration.** IEEE-123 MF01 Simple and MF02 Exotic variants, with authoritative health/fault locks and switch controls. RBC structural graph controller, screened selected-route continuation, and P2 MPC MILP with 2-step horizon.
- **Native and baseline studies.** B00 original native-control time-series runner and PESGM experimentation scripts remain preserved in their original directories.
- **Paper-ready reference data.** Example input contains IEEE-123 *diagram* coordinates, switch positions and selected audited CSVs, clearly separated from new simulations.

## Architecture in one minute

```text
  DSS feeder files + user ProblemSpec + exogenous data
                 |                 |
                 v                 v
   circuit/inventory/semantic registries -----> resolved capabilities
                 |                                  |
                 v                                  v
     OpenDSSSimulator (Gymnasium) <-------- compiled observation/action spaces
        |            |         |
        | reset/step |         +-- public action audits / history / clock
        |            |
        v            v
  native AltDSS AC   ControllerContext (detached, read-only)
        ^                        |
        |                        v
        +---- authorized action <-- RBC / MPC / your own controller
```

Every controller must use the published observation/action contracts. Changing a specific controller does **not** authorize changes to frozen simulator internals. See [API walkthrough](docs/tutorial/01_PUBLIC_API.md), [architecture boundary](docs/tutorial/02_ARCHITECTURE.md) and [controller reference](docs/tutorial/03_CONTROLLER_PROGRAMMING.md).

## Repository layout

| Directory | Purpose and status |
|---|---|
| [`examples/`](examples/README.md) | **Recommended standalone 01-10 examples**; editable configuration, clear closed-loop loops, input/output conventions |
| `examples/Input/` | IEEE-123 feeder files, synthetic time series, controller cases and provenance; keep inputs unchanged |
| `examples/Output/` | Optional per-example output, including histories, diagnostics, audits, CSV/JSON; typically ignored by Git |
| `examples/ieee123_course/` | **Legacy course under construction**; retained for reference, not recommended as the primary tutorial |
| `src/opendsssim/` | AltDSS backend, semantic registries, `ProblemSpec`, environment, runtime, information services, controllers |
| `experiments/pesgm2027/` | Original research feeder definitions, pilots and scientific experiment scripts |
| `tests/` | Simulator/controller tests |
| `docs/tutorial/` | Architecture, public APIs, programming contracts, science limitations, testing, citations |
| `docs/development/` | Detailed scientific design contracts and development records |
| `docs/release/` | Source provenance and publication checklist |
| `results/pesgm2027/` | Historical research evidence (do not conflate archived results with fresh tutorial runs) |

### Recommended examples directory

```text
OpenDSSSim/
|-- README.md
|-- CITATION.cff
|-- pyproject.toml
|-- src/opendsssim/
|-- examples/
|   |-- README.md
|   |-- 01_IEEE123_Environment_Basics.py
|   |-- 02_IEEE123_TimeSeries_NoController.py
|   |-- 03_Inspect_Saved_Results.py
|   |-- 04_IEEE123_ProblemSpec_Observations.py
|   |-- 05_IEEE123_ProblemSpec_Actions.py
|   |-- 06_IEEE123_Controller_Context_Forecasts.py
|   |-- 07_IEEE123_P1_RBC.py
|   |-- 08_IEEE123_P1_MPC.py
|   |-- 09_IEEE123_P2_RBC.py
|   |-- 10_IEEE123_P2_MPC.py
|   |-- Input/                       # IEEE123_Base, IEEE123_P1, P2 variants, cases, replay
|   |-- Output/                      # Optional saved run results
|   `-- ieee123_course/              # Legacy, under construction
|-- docs/
|-- experiments/pesgm2027/
|-- results/pesgm2027/
`-- tests/
```

## Installation and dependencies

Python **3.10+** is required (`pyproject.toml`). Core dependencies are `altdss==0.2.4` and `gymnasium>=1.2,<2`; plotting and data inspection may additionally use NumPy and Matplotlib. Gurobi is **optional** and required only for MPC lessons; follow Gurobi's separate licensing conditions. `pip install -e ".[dev]"` enables the existing pytest suite.

The **standalone examples 01-10** were authored and checked offline but have **not** been independently native-run as a complete tutorial sequence. Run native AltDSS and (for MPC) licensed Gurobi smoke tests before publishing execution-success claims. The older course has separate development-only checks and is not the supported tutorial path. See [test guide](docs/tutorial/05_TESTING_AND_REPRODUCIBILITY.md).

## Scientific scope and honest comparisons

- P1 RBC and MPC demonstration setups are educational and need not reproduce the previously archived S10C/A07A3 protocol exactly; archived outcomes retain their provenance.
- P2 RBC's 24-step demonstration **continues previously electrically screened S10D routes**, checking fresh structural previews and physical AC outcomes. It does **not** implement a newly qualified per-step dynamic electrical evaluator.
- P2 MPC's original code is **slack-first**; service-first is a **separate sensitivity** that swaps only Gurobi objective priorities. It is not the original ratified optimization freeze.
- Bus-connected demand and connected kWh are **topology-based nominal proxies**, not metered AC-delivered energy. Voltage-only qualification does **not** establish thermal security, phase-aware radiality certification, or utility switching safety.
- Offline case `dt_hours=0.25` and the demonstration's hourly physical replay are different; do not conflate objective-unserved kWh with measured 24-hour energy.
- The bundled IEEE-123 coordinates are illustrative one-line **diagram positions**, not geographic latitudes/longitudes.

## How to cite OpenDSSSim

**Cite the software and the paper separately.** A citation to the source code identifies the specific implementation and version, while a citation to the research paper (once formally published) supports framework design and experimental claims.

**Software (current prerelease, provisional attribution):**

> OpenDSSSim contributors, *OpenDSSSim: A Generalized Gymnasium Framework for Distribution-System Simulation and Control*, software version `0.1.0a6`, 2026. Repository URL and exact Git commit to be added after the GitHub repository is created.

Use this BibTeX template now, and replace the provisional author group, repository URL and commit with the approved publication information:

```bibtex
@software{OpenDSSSim_v0_1_0a6,
  author  = {{OpenDSSSim contributors}},
  title   = {{OpenDSSSim}: A Generalized Gymnasium Framework for Distribution-System Simulation and Control},
  year    = {2026},
  version = {0.1.0a6},
  note    = {Research software. Add public GitHub URL and exact commit SHA before publication.}
}
```

<<<<<<< HEAD
The repository contains a **provisional** [`CITATION.cff`](CITATION.cff), enabling GitHub's **Cite this repository** interface once pushed. **Before making the repository public**, the copyright holder(s) must approve the actual software author roster and fill in the GitHub repository URL; do not assume the provisional collective author represents the final paper authors.

**Associated paper:** *OpenDSSSim: A Generalized Gymnasium Framework for Distribution-System Simulation and Control*, planned for IEEE PES General Meeting 2027. **Do not invent a DOI, proceedings page number, acceptance status, or publication date.** Cite the manuscript as *in preparation* only when appropriate and approved; replace with the final IEEE citation once published.

For research reproducibility, report the OpenDSSSim version **and exact Git commit**, feeder variant (`ieee123_pesgm2027`, `ieee123_p2_mf01_simple`, or `ieee123_p2_mf02_exotic`), controller and objective policy, timestep, AltDSS and Gurobi versions where applicable, random seed, and result evidence hashes. See [Citation and reproducibility](docs/tutorial/06_CITATION_AND_REPRODUCIBILITY.md).

## Contributing, licensing and responsible public release

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), [scientific limitations](docs/tutorial/04_SCIENTIFIC_LIMITS.md), [testing and reproducibility](docs/tutorial/05_TESTING_AND_REPRODUCIBILITY.md), and the [GitHub publication checklist](docs/release/GITHUB_PUBLICATION_CHECKLIST.md).

The current repository tree includes a `LICENSE` file, but public distribution rights, attribution and the status of that license still need confirmation; original feeder files and reference data may carry different terms. Review the 12 machine-local path matches identified in the release audit before a public push. Until these are resolved, keep the GitHub repository private. Do not treat the presence of a file named `LICENSE` as proof that all third-party materials can be redistributed under its terms.
=======
>>>>>>> a981684afa7018fb8e338fd5cccf967d74089e64
