# OpenDSSSim

**A generalized Gymnasium interface for electric distribution-system simulation and control, backed by AltDSS.**

OpenDSSSim separates a physical feeder and power-flow engine from its **problem declaration**, **semantic observations**, **authorized actions**, **time-series environment**, and **controller algorithms**. The objective is to make distribution-system control studies reproducible without embedding one control problem—or one controller—inside the simulator itself.

> **Research software / prerelease (`0.1.0a6`).** This repository is a teaching/research snapshot, not a certified utility operations platform. It is not suitable for safety-critical grid switching. A project-level public license has **not yet been selected**; review [LICENSE_REVIEW_REQUIRED.md](LICENSE_REVIEW_REQUIRED.md) before publishing or inviting external redistribution.

## Documentation map: choose your starting point

| Your goal | Start here | What you will achieve |
|---|---|---|
| Install and verify the repository | [Installation](#installation-and-dependencies), [test guide](docs/tutorial/05_TESTING_AND_REPRODUCIBILITY.md) | Set up the package and run integrity/native smoke tests |
| Learn OpenDSSSim from zero | [IEEE-123 course](examples/ieee123_course/README.md) | Complete 11 lessons with inputs, outputs and annotated code |
| Understand the simulator layers | [Architecture](docs/tutorial/02_ARCHITECTURE.md) | Trace feeder, registries, problem contract, controller context and `env.step` |
| Write a new problem/controller | [Public API](docs/tutorial/01_PUBLIC_API.md), [controller programming](docs/tutorial/03_CONTROLLER_PROGRAMMING.md) | Use `ProblemSpec`, layouts and authorized actions without backend bypass |
| Study RBC and MPC | [Lesson 06–09 guide](examples/ieee123_course/README.md) | Compare P1 Volt/VAR with P2 MF01/MF02 restoration |
| Reproduce a campaign | [Course campaign](examples/ieee123_course/README.md), [testing](docs/tutorial/05_TESTING_AND_REPRODUCIBILITY.md) | Generate independent run directories and evidence receipts |
| Make plots and cite results | [Lesson 10](examples/ieee123_course/README.md), [citation](docs/tutorial/06_CITATION_AND_REPRODUCIBILITY.md) | Plot bus voltages, switch maps and report precise software/protocol versions |

## Start here: the interactive IEEE-123 course

The new [IEEE-123 self-contained course](examples/ieee123_course/README.md) is the recommended entry point. It includes **four original feeder variants**, qualified static MPC case inputs, original S10D RBC route evidence, example observations/plotting data, and a run-isolated `output/` folder. Examples are richly commented and never patch the simulator or feeder.

```powershell
# Windows PowerShell, from this repository's root
conda create -n opendsssim-demo python=3.11 -y
conda activate opendsssim-demo
python -m pip install -e ".[dev]"
python -m pip install -r examples/ieee123_course/requirements-tutorial.txt

# No Gurobi needed: provenance and input-integrity verification
python examples/ieee123_course/run_course.py --lesson 00 --run-id check_001

# Native AltDSS / Gymnasium circuit loading
python examples/ieee123_course/run_course.py --lesson 01 --run-id snapshot_001

# Full course (MPC lessons require gurobipy and a valid solver license)
python examples/ieee123_course/run_course.py --all --steps 3 --run-id course_001
```

The full six-run **24-step research demonstration** (P1 RBC/MPC and P2 MF01/MF02 RBC/MPC) is explicitly opt-in because it requires a working Gurobi license and is computationally more expensive:

```powershell
python -m pip install gurobipy
python examples/ieee123_course/run_course.py --paper-campaign --steps 24 --run-id pesgm_trial_001
```

A single command creates `examples/ieee123_course/output/<run-id>/`, with individual lesson results, native voltage data, local registry/inventory/preflight receipts, and a final campaign receipt. Existing output folders are never overwritten.

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

| Directory | Purpose |
|---|---|
| `src/opendsssim/` | Physical backend, discovery, persistence, semantic registries, problem resolution, runtime, environment, controllers |
| `experiments/pesgm2027/feeders/` | Source feeder variants, including IEEE-123, IEEE-8500, European LV feeders |
| `experiments/pesgm2027/` | Original research experimentation code and baseline studies |
| `examples/ieee123_course/` | **New, self-contained and annotated** learning campaign with `input/` and `output/` |
| `tests/` | Existing simulator/controller unit and integration tests |
| `docs/development/` | Authoritative research and ratified mathematical contracts |
| `docs/tutorial/` | Task-oriented public-API programming guide |
| `docs/release/` | Input provenance, release differences, publication checklist |
| `results/pesgm2027/` | Existing archived qualified research evidence |

### Detailed learning-tree view

```text
OpenDSSSim/
├── README.md                         main installation, learning and citation guide
├── CITATION.cff                      provisional GitHub software citation
├── pyproject.toml                    Python package and dependency metadata
├── src/opendsssim/                   existing simulator, contracts and controllers
├── experiments/pesgm2027/           original feeder definitions and research runners
├── examples/ieee123_course/
│   ├── README.md                     full syllabus and commands
│   ├── input/                        feeders, static cases, RBC routes, geometry, manifests
│   ├── lessons/                      annotated lessons 00 through 10
│   ├── course_utils/                 shared public-interface teaching utilities
│   ├── run_course.py                 lesson and paper-campaign CLI
│   ├── tests/                         offline tutorial checks
│   └── output/                       run-specific results, kept out of source control
├── docs/tutorial/                    API, architecture, controller, scientific and test guides
├── docs/development/                 full research/development records
├── docs/release/                     provenance and publication checklists
├── tests/                            existing OpenDSSSim unit/integration tests
└── scripts/                          release verification
```

The `input/` directory is source-pinned and read-only by convention. Each invocation uses a unique `output/<run-id>/` and does not overwrite earlier results. Source-feeder and diagram-coordinate files are preserved with attribution/provenance notes; diagram XY positions are **not** geographic coordinates.

## Installation and dependencies

Python **3.10+** is required (`pyproject.toml`). Core dependencies are `altdss==0.2.4` and `gymnasium>=1.2,<2`; the tutorial additionally uses NumPy and Matplotlib. Gurobi is **optional** and required only for MPC lessons; follow Gurobi's separate licensing conditions. `pip install -e ".[dev]"` enables the existing pytest suite.

A native AltDSS, Gurobi or full scientific campaign run has **not been executed in the package-building environment**. We verified syntax, input case hashes, teaching CLI, offline lesson tests, and reference plotting; run the documented native smoke sequence on a configured machine before publishing execution claims. See [test guide](docs/tutorial/05_TESTING_AND_REPRODUCIBILITY.md).

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
@software{OpenDSSSim_v0_1,
  author  = {{Ninad Gaikwad and Anamika Dubey}},
  title   = {{OpenDSSSim}: A Generalized Gymnasium Framework for Distribution-System Simulation and Control},
  year    = {2026},
  version = {0.1.0a6},
  note    = {Research software. Add public GitHub URL and exact commit SHA before publication.}
}
```

