# Tutorial 2 — Framework structure and strict boundaries

## Layer 1: circuit source and backend

`network/loading.py` establishes circuit source identity; `backends/base.py` defines the backend boundary; `backends/altdss_backend.py` implements the AltDSS adapter; `plant/core.py` manages compile/reset/solve. The physical backend is **not** an action interface available to a controller.

## Layer 2: discovery and persistent semantic inventory

`discovery/` extracts engine/circuit capabilities. `persistence/` maintains circuit inventory, semantic registry, manifest and preflight verification. `semantics/` compiles native properties, quantities and policy. These layers allow the simulator to reason about a feeder without hardcoding IEEE-123 nodes into control algorithms.

## Layer 3: problem resolution, action authority and Gym spaces

`problem/schema.py` defines `ProblemSpec`, selection groups, semantic queries, action restrictions, fault and control authority. `problem/resolution.py` resolves them against the actual inventory/registry. `problem/spaces.py` compiles typed Gym observation/action leaves. A generic controller must respect resolved device paths and exact shapes, not hardcode backend calls.

## Layer 4: public runtime and time

`runtime/` binds selected quantities and stores step audits/history. `environment/` supplies `reset`, `step`, `controller_context`, episode time, replay, forecasts and uncertainty. Note the distinction between **decision-time** data and post-step **realized AC** data. Actual physical changes occur only within the simulator during `env.step`.

## Layer 5: independent controllers

`controllers/reference/` implements rule-based P1 and structural P2 RBC. `controllers/mpc/` contains data contracts, LinDistFlow parameter mappings, P1 MIQP, P2 MILP, action encoders and closed-loop integration. No controller should import and mutate the AltDSS backend directly.

## Example-agnosticism matrix

| Independent dimension | IEEE-123 examples | Framework API |
|---|---|---|
| Circuit | Baseline, 10-PV P1, MF01, MF02; separate 8500/906 feeder inputs also exist | `OpenDSSSimulator(network)` |
| Problem | Native baseline, Volt/VAR, restoration | `ProblemSpec` |
| Controller | Native controls, RBC, MPC, future RL | `ControllerContext`, `action_layout`, `env.step` |
| Time/data | Snapshot, constant replay, explicit profiles and forecasts | `EpisodeSpec`, `ReplaySpec`, `exogenous_forecast` |
| Evidence | AC voltages, action audits, history, topology proxies | `info`, `history`, output CSV/JSON |

The tutorial **does not claim all controllers can be applied unchanged to every feeder**. Feeder agnosticism is a published interface/capability property, contingent on the selected feeder supplying the requested semantics and devices.

## Relationship to frozen research evidence

The original 510-file qualified research predecessor should be preserved when comparing with published PESGM experiments. This GitHub-ready copy replaces only its old two-line root `README.md` for onboarding and **adds** educational paths. All executable `src/opendsssim/` sources remain byte-for-byte identical to the upload. The detailed source diff is in `docs/release/RELEASE_SOURCE_PRESERVATION.json`.
