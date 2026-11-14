# Tutorial 1 — OpenDSSSim public API, by contract

This is a guided technical reference to **the actual interfaces in the uploaded source**, not pseudocode for a hypothetical simulator. Start with the runnable course at `examples/ieee123_course/`.

## A. Source circuit and semantic inventory

```python
from pathlib import Path
from opendsssim.environment import OpenDSSSimulator

network = Path('examples/ieee123_course/input/feeders/ieee123_base/IEEE123Master.dss')
env = OpenDSSSimulator(network, inventory_dir=Path('output/inventory'))
try:
    obs, info = env.reset(seed=511)  # solves a native AC snapshot
    assert info['solution']['converged']
    discovery = env.discover_circuit()
    inventory = env.circuit_inventory
    print('buses',len(inventory.buses),'objects',len(inventory.objects))
finally:
    env.close()
```

`OpenDSSSimulator` can discover equipment and solve a native snapshot even without a `ProblemSpec`, but in that case it exposes a minimal observation space (`converged`) and an empty action space. If you need bus voltages and permitted actions as controller inputs, declare them via the problem contract first.

The environment's physical `OpenDSSPlant` and backend are implementation details. **Do not use `env._plant`, direct `altdss` methods, or raw DSS commands to bypass the controller action contract.**

## B. ProblemSpec: define what a controller may read and command

```python
from opendsssim.controllers.reference import make_p1_problem
problem = make_p1_problem(
    pv=('PVSystem.pvd105', ...),
    capacitors=('Capacitor.c83', ...),
    transformers=('Transformer.reg1a', ...),
)
```

The ellipses above indicate omitted entities; **the code as written is illustrative, not a complete runnable problem**. For a working 10-PV/4-capacitor/7-regulator example, Lesson 02 reads all exact entities from the pinned case JSON and passes complete tuples.

The reference factory chooses semantic observations (`bus_voltage_pu`, capacitor states and transformer tap positions) and action channels (`pv_reactive_power_command`, `capacitor_state`, `transformer_tap_command`). It also declares **external authority** over exactly those devices; the original native RegControls must not simultaneously control their taps.

On construction, the environment prepares and resolves this contract before the first control step. Use:

```python
env = OpenDSSSimulator(network, problem=problem)
obs, info = env.reset(seed=511)
ctx = env.controller_context(include_static_network=True)
print(ctx.observation_space_sha256)
print(ctx.action_space_sha256)
for entry in ctx.action_layout:
    print(entry['path'],entry['shape'],entry['space_type'],entry['domain_values'])
```

The `action_layout` is **authoritative**. Do not assume a three-phase capacitor bank has three independent physical switch commands: C83 is a single physical bank action even though it contributes reactive injection to three phases. Use `env.action_space.contains(action)` and respect exact numeric/categorical shapes.

## C. ControllerContext: read-only information entitlement

`ControllerContext` exposes `schema_version`, `episode_id`, `completed_steps`, `decision_time_utc`, `electrical_sample_time_utc`, `observation`, space hashes, `action_layout`, authorized `devices`, `static_network`, `last_realized_action_feedback`, and an optional qualified `forecast`.

The `static_network` describes physical elements and terminal bus specifications, not an AC feasibility certificate. `commandability='EXTERNAL_READY'` denotes positive readiness; unknown readiness is not permission to switch. Fault-disabled equipment is locked even if an optimizer requests it.

```python
ctx = env.controller_context(forecast_horizon=12, required=False,
                             include_static_network=True)
for device in ctx.devices:
    print(device.native_entity,device.commandability)
# ctx.to_dict() is detached and JSON-compatible, not a backend reference.
```

A forecast request reads declared exogenous/replay signals only. A controller cannot request an arbitrary future real-world load or recover private noise draws through this API. With no source and `required=False`, an unavailable forecast is an explicit status, not an invented perfect prediction.

## D. Complete action encoding and step

```python
from opendsssim.controllers.reference import encode_action

# `commands` must map every authorized (native entity, semantic quantity)
# tuple to exactly one permitted value. For a P2 branch command the semantic
# categorical state is 'CLOSED' or 'OPEN' (encoded using the published layout).
action = encode_action(ctx, commands)
if not env.action_space.contains(action):
    raise ValueError('Action incompatible with compiled Gym space')
new_obs, reward, terminated, truncated, info = env.step(action)
```

Each official step applies authorized commands, solves AC, captures observation, and provides an `action_audit`. A returned `status='ADMISSIBLE_APPLIED'` does **not** universally prove physical realization equals the requested state; compare the `realized_value`. For a branch, the realized value records terminal-open flags. For a capacitor, compare the actual state to the requested bank state when present.

## E. Episode and recording

```python
from opendsssim.environment import EpisodeSpec
spec = EpisodeSpec(max_steps=24, dt_seconds=3600)
# episode_spec is passed to constructor when not using ReplaySpec
```

The external `EpisodeClock` timestamps Gym decision and electrical samples. It does not command AltDSS's internal control clock. `env.history` retains the selected history level. At each step `info['time']['completed_steps']` should increase and `info['solution']['converged']` should be checked before claiming an electrical result. Reset creates an additional AC sample, so **24 steps** normally correspond to **25 electrical sample instants**.

## F. Replay, forecasting and uncertainty

The authoritative B00 example function `make_replay()` constructs explicit physical load and PV profiles and returns a `ReplaySpec` with a declared `ReplaySource` and `ReplayBinding`. A `ReplaySession` owns time and physical truth when supplied: do not pass `episode_spec` and `exogenous_replay` simultaneously. See Lesson 04 and `src/opendsssim/environment/{replay,forecast,uncertainty}.py` for coverage and noise contracts.

## G. Discovery, performance, recorders and capability access

| Interface | What it means | Where to learn |
|---|---|---|
| `discover_engine()` | Backend engine capabilities | Lesson 01 |
| `discover_circuit()` | Loaded physical circuit metadata | Lesson 01 |
| `circuit_inventory` | Canonical circuit object/element/bus inventory | Lessons 01/05 |
| `semantic_registry` | Resolved canonical semantic measurement/action entries | Lesson 02 and A03 docs |
| `resolved_problem` | Qualified problem selection with stable identity | Lesson 02 |
| `runtime_binding` | Semantic action and observation bindings | B00 runner, Lesson 02 |
| `observation_space`, `action_space` | Exact Gymnasium runtime spaces | Lesson 02 |
| `controller_context()` | Authorized, detached decision view | Lesson 05 |
| `exogenous_forecast()` | Source-bounded future inputs | Lesson 04 |
| `episode_clock` | Read-only logical time | Lesson 03 |
| `history` | Runtime step/history recorder | Lesson 03 |
| `native_diagnostics()` | Explicit diagnostic endpoint | B00 original experiment |
| `last_result` | Latest physical solve result | Lesson 01 |

These public methods/properties are in `src/opendsssim/environment/simulator.py`. Availability of a property does not imply a particular action is authorized: the resolved `ProblemSpec` governs control.

## H. What is not supported or certified

- Native electrical switching and transformer/capacitor semantics must not be bypassed to “fix” a controller.
- P2 RBC's structural preview is **not** a fresh electrically qualified route.
- P2 MILP is a multiphase **linearized** model; thermal certification is absent where source ratings are unavailable.
- The provided examples do **not** expose phase-specific native bus-coordinate locations; coordinates are illustrations only.
