# OpenDSSSim IEEE-123: a guided, self-contained programming course

**Goal:** after completing this repository-local campaign you should be able to write a new OpenDSSSim problem/controller client without editing `src/opendsssim/` or directly commanding AltDSS.

## Input, output, and code separation

```text
examples/ieee123_course/
  README.md                    this learning guide
  input/                       IMMUTABLE, SHA-256 manifest checked at launch
    feeders/                   IEEE-123 baseline / P1 / P2 MF01 / P2 MF02
    mpc_baseline/              qualified A07A2 static LinDistFlow cases
    qualified_routes/          original S10D RBC selected-route evidence
    geometry/                  bus diagram coordinates and switch locations
    reference_results/         historical paper plots / comparison CSVs
  lessons/                     one heavily commented Python module per facet
  course_utils/                public-interface-only helper routines
  scripts/run_windows.ps1      Windows runner
  scripts/run_bash.sh          POSIX runner
  tests/test_course_integrity.py
  output/                      every run creates a new unique run ID
  run_course.py                one command interface
```

Use **only** `input/` for static inputs. The course writes replay profiles, inventory/semantic registry receipts, preflight outputs, action audits, bus-voltage CSVs, and run JSON into `output/<run-id>/lesson_XX/` or `output/<run-id>/<experiment>/`. Example outputs are reproducible run artifacts and are not silently edited into the feeder.

## Install

```powershell
# From repository root, in a Python 3.10+ environment
python -m pip install -e ".[dev]"
python -m pip install -r examples/ieee123_course/requirements-tutorial.txt
# ONLY when running the MPC lessons:
python -m pip install gurobipy
```

You must have a compatible AltDSS runtime installed and—only for MPC—a functioning Gurobi license. The original `pyproject.toml` pins `altdss==0.2.4`. Some systems need their own environment/toolchain setup.

## Learning path: eleven deliberately small lessons

| Lesson | Question you will answer | Interfaces exercised | Needs Gurobi? |
|---|---|---|---|
| `00` | What exactly is the input and is it unchanged? | SHA-256 provenance and safe outputs | No / no AC |
| `01` | How do I load IEEE-123 and solve a native snapshot? | `OpenDSSSimulator`, circuit/engine discovery, reset | No |
| `02` | How do semantic contracts become Gym spaces? | `ProblemSpec`, resolution, `action_layout`, action/observation hashes | No |
| `03` | What happens over time? | `reset`, `step({})`, `EpisodeSpec`, `history`, `info['time']` | No |
| `04` | Where does changing physical demand and forecast data come from? | `ReplaySpec`, declared B00 replay, public forecast | No |
| `05` | What does a controller know—and not know? | `ControllerContext`, authorized devices, static network | No |
| `06` | How do I implement a three-channel Volt/VAR RBC? | `P1RuleBasedController.decide`, complete action, AC readback | No |
| `07` | How do I integrate predictive MIQP without touching the plant? | `update_p1`, `step_once`, Gurobi, native AC | Yes |
| `08` | How does restoration graph logic differ from native switching? | `P2GraphController.preview`, S10D screened route, `env.step` | No |
| `09` | How do hard constraints and objective priorities affect service? | `solve_p2`, `step_once`, optional in-memory service-first sensitivity | Yes |
| `10` | How do I create publication figures using reference outputs? | Matplotlib, voltage data, geometry provenance | No / no AC |

### Run lesson 00 first (needs only NumPy)

```powershell
python examples/ieee123_course/run_course.py --lesson 00 --run-id provenance_001
```

The course checks every `input/` file against `input/SHA256_INPUT_MANIFEST.csv` before running any lesson. Edit an input to see it fail closed; restore the input before proceeding.

### Native snapshot / contract / temporal steps

```powershell
python examples/ieee123_course/run_course.py --lesson 01 --run-id first_ac
python examples/ieee123_course/run_course.py --lesson 02 --run-id first_problem
python examples/ieee123_course/run_course.py --lesson 03 --steps 3 --run-id first_clock
python examples/ieee123_course/run_course.py --lesson 04 --steps 3 --run-id first_forecast
python examples/ieee123_course/run_course.py --lesson 05 --run-id first_context
```

Read `output/first_problem/lesson_02/result.json`. The `action_layout` tells you exactly which native entities and semantic quantities are authorized and which Gym shapes each action requires. You should never construct a controller command by guessing what the backend will accept.

### First real controllers

```powershell
python examples/ieee123_course/run_course.py --lesson 06 --steps 3 --run-id p1_rbc_demo
python examples/ieee123_course/run_course.py --lesson 07 --steps 3 --run-id p1_mpc_demo
python examples/ieee123_course/run_course.py --lesson 08 --steps 3 --run-id p2_mf01_rbc
python examples/ieee123_course/run_course.py --lesson 08 --steps 3 --variant ieee123_p2_mf02_exotic --run-id p2_mf02_rbc
python examples/ieee123_course/run_course.py --lesson 09 --steps 3 --policy slack-first --run-id p2_mf01_slack
python examples/ieee123_course/run_course.py --lesson 09 --steps 3 --policy service-first --run-id p2_mf01_service
python examples/ieee123_course/run_course.py --lesson 09 --steps 3 --variant ieee123_p2_mf02_exotic --policy service-first --run-id p2_mf02_service
```

**Interpretation matters:** the two P2 MPC modes are **different objective policies**, not competing electric network parameterizations. The service-first mode loads the identical source solver in memory and reorders only operational slack and unserved-energy priorities. No feeder, frozen plant, or installed controller source is edited. RBC's `preview` is a structural preview; without a qualified electrical evaluator, `decide()` must *not* be invoked as if it were a fresh native-feasible controller. The S10D continuation uses previously screened routes and rechecks them with new AC steps.

### Complete six-run 24-step teaching campaign

```powershell
python examples/ieee123_course/run_course.py --paper-campaign --steps 24 --run-id final_24h_001
```

The opt-in campaign runs P1 RBC/MPC, P2 MF01 RBC/MPC service-first, and P2 MF02 RBC/MPC service-first, six separate 24-step episodes. It will create **144 native post-reset steps if all pass**. Existing output folders are never overwritten. There is no automatic retry on an infeasible/failed case; partial evidence remains for audit. The demonstration is constant synthetic hourly replay and is not a historical operating-day calibration.

### No-AC plotting demonstration

```powershell
python examples/ieee123_course/run_course.py --lesson 10 --run-id plots_001
```

The reference CSVs and switch coordinates are already in `input/`. For detailed topology plotting, study `input/geometry/switch_positions.csv` and the original `P2Branch` node/phase definitions in the static case JSONs. Coordinates are one-line diagram positions only.

## Five essential client contracts

1. **Circuit** — `OpenDSSSimulator(network=...)` takes a DSS master file; `source_root` can support a different logical source-root when needed. Native circuit loading does not imply controller authority.
2. **Problem** — `ProblemSpec` selects authorized semantic observations/actions and faults; the environment resolves the contract before control starts.
3. **Information** — `env.controller_context(...)` returns a detached, read-only decision-time object with bounded entitlement and optional explicit forecast.
4. **Action** — use `encode_action(ctx, complete_commands)` or an authorized controller adapter, verify `env.action_space.contains(action)`, then call `env.step(action)`.
5. **Evidence** — inspect `info['action_audit']`, `info['solution']['converged']`, the logical clock, and **realized native state**, not only requested commands or solver success.

### How to develop a new controller

```python
ctx = env.controller_context(forecast_horizon=2, required=False)
# A controller builds a *complete* action mapping from ctx.action_layout.
action = my_controller(ctx)
assert env.action_space.contains(action)
next_obs, reward, terminated, truncated, info = env.step(action)
assert info['solution']['converged']
# A status of ADMISSIBLE_APPLIED does not always guarantee a native
# capacitor's realized state equals its requested state. Audit readbacks.
```

**Never** access `env._plant`, `env._access`, mutable backend objects or `altdss` directly from the educational client. The package's source-level implementation may use these internally; they are not authorized controller APIs.

## Exercises and grading rubric

- **Exercise A:** Change only the `ProblemSpec` selection in a new user script and predict the resulting layout/hashes. Confirm via Lesson 02. Do not edit the original factory source.
- **Exercise B:** Change `EpisodeSpec.dt_seconds` in a copied lesson and show the clock difference. Do not confuse the clock with physical load replay.
- **Exercise C:** Show that `forecast_horizon=2` with no qualified exogenous source does not invent future demand.
- **Exercise D:** Intentionally omit one action channel in a scratch controller and verify the encoder rejects it before `env.step`.
- **Exercise E:** Compare P2 slack-first and service-first models on a fixed input. Explain which constraints are hard and which voltage violations are modeled using slack.
- **Exercise F:** For MF01/MF02, compare RBC and MPC switch paths that connect the same nominal kW. Explain why equality of connected kW does not imply identical restoration routes or metered AC energy.

See [public API walkthrough](../../docs/tutorial/01_PUBLIC_API.md) and [testing guide](../../docs/tutorial/05_TESTING_AND_REPRODUCIBILITY.md) for expanded worked examples.
