# OpenDSSSim A0 — SmartCommunitySim_2 Architecture Audit and A01 Boundary

**Document ID:** `OpenDSSSim_A0_SmartCommunitySim2_ReuseAdaptNewMatrix_v01_20260930`  
**Status:** PROPOSED FOR RATIFICATION  
**Date:** 2026-09-30  
**Intended repository path:** `docs/development/architecture/OpenDSSSim_A0_SmartCommunitySim2_ReuseAdaptNewMatrix_v01_20260930.md`

## 1. Directed-Input Authority

Reviewed bundle:

`SmartCommunitySim_2_OpenDSSSim_A0A01_DirectedInput_v01_20260930_200401.zip`

Authoritative bundle SHA256:

`70F7623D8D8354B053C3C62B41587E8888DFA4E1933FD19569A95CB9BB1627F5`

Source repository:

`C:\Users\ninad\Dropbox\NinadGaikwad_PhD\Gaikwad_Research\Gaikwad_Research_Work\SmartCommunitySim_2`

Source files reviewed: **101**

The bundle source inventory was rehashed after extraction; all 101 source-file hashes matched the supplied inventory.

## 2. Audit Purpose

SmartCommunitySim_2 is used as an architectural reference only.

The goal is not to port SmartCommunitySim community science into OpenDSSSim. The goal is to identify proven software boundaries, runtime patterns, qualification practices, and persistence concepts that should inform a clean OpenDSSSim implementation.

The four decision classes are:

- **REUSE** — reuse the architectural concept/pattern.
- **ADAPT** — preserve the architectural intent but redesign the implementation around AltDSS/OpenDSS semantics.
- **NEW** — OpenDSSSim requires a capability that SmartCommunitySim_2 does not provide.
- **IMMUTABLE / REFERENCE-ONLY** — study for context but do not copy into OpenDSSSim.

## 3. REUSE

| SmartCommunitySim_2 pattern | OpenDSSSim decision |
|---|---|
| `src/` package layout with `pyproject.toml` | Reuse the modern package-layout pattern. |
| Separate `backends/`, `plant/`, `environment/`, `controller_runtime/` | Reuse the layer separation. |
| `gym.Env` public lifecycle using `reset()` / `step()` | Reuse as the canonical external plant boundary. |
| Backend factory/injection concept | Reuse the concept; AltDSS is the first production backend. |
| Controller code outside plant physics | Reuse strictly. Controllers never mutate AltDSS directly. |
| Typed/frozen runtime schemas | Reuse for OpenDSS capability/state/action/problem/runtime schemas. |
| Explicit episode specification and seed provenance | Reuse. Keep environment, initialization, controller, profile/noise seeds separable. |
| Forecast as a service separate from the plant | Reuse the service boundary. |
| Recorder separated from plant/controller science | Reuse. |
| Recorder has a true high-throughput fast path | Reuse the performance principle. |
| Offline readers/analysis consume finalized recordings | Reuse. |
| Standardized run envelope and run-manifest lifecycle | Reuse. |
| Atomic manifest updates and artifact registration | Reuse. |
| Unit + integration + compatibility/regression qualification | Reuse the testing philosophy. |
| Source/behavior qualification rather than class-name-only tests | Reuse. |
| External controller timing instrumentation | Reuse. |
| Same plant/data/constraints across controller comparisons | Reuse as a PESGM fairness invariant. |

## 4. ADAPT

| SmartCommunitySim_2 concept | OpenDSSSim adaptation |
|---|---|
| `PlantBackend` ABC | Replace community-specific methods with a narrow electrical-network backend contract: context creation, compile/load, set inputs, set controls, solve snapshot, read quantities, convergence/status, close. |
| MATLAB/Python backend factory | Adapt to `AltDSSBackend` first. Do not recreate MATLAB/Python duality. Leave the abstraction open for future backends only if justified. |
| `community/catalog.py` and materialization | Adapt to `network/` catalog, feeder loading/materialization, provenance, normalization, and benchmark freeze. |
| Device registry | Expand from a small hand-built device dictionary to discovered OpenDSS object/capability registries. |
| Static/dynamic controller context | Adapt to immutable circuit/problem specifications plus a current solved-state/context view. |
| Community device map | Adapt to stable native DSS object identities, selectors, buses, terminals, phases, windings, and problem mappings. |
| Load/weather processing | Adapt to generic externally supplied exogenous profile providers for Load/PV/weather/events. |
| Time slicing | Adapt to explicit OpenDSSSim clock and profile indexing. |
| Forecast provider | Adapt to problem-selected forward views of the externally owned profile source. Forecasting must not advance AltDSS. |
| `EpisodeRuntime` | Adapt to externally orchestrated snapshot power-flow stepping with OpenDSSSim-owned time. |
| User observation/action callbacks | Replace/extend with declarative `ProblemSpec` + structured spaces; wrappers may flatten/normalize. |
| Reward/termination/truncation hooks | Move into optional `ProblemSpec`; no-control simulation remains valid without a control problem. |
| Action realization | Generalize to native DSS controls with validation, optional projection policy, control-authority ownership, and realized post-solve values. |
| `minimal/standard/debug` recorder tiers | Split into two independent axes: H0–H3 history-retention level and FAST/STANDARD/AUDIT execution profile. |
| Modern recorder disables legacy growing X/U histories | OpenDSSSim instead maintains an always-present secondary history interface whose retained detail is controlled by H0–H3. |
| Run manifest `git_commit` | Before GitHub exists, add source-manifest SHA256, architecture-document ID, latest patch ID, machine role, and environment/runtime versions. Git commit becomes additional provenance after release. |
| Community performance registry | Adapt to distribution-system metrics and problem-specific metrics; keep registry-driven definitions/units/applicability. |
| Result directories | Adapt to OpenDSSSim run artifacts while preserving collision-safe run envelopes. |

## 5. NEW

The following should be designed natively for OpenDSSSim.

### 5.1 AltDSS context ownership

One instantiated `OpenDSSSimulator` owns one independent AltDSS context.

Different Gymnasium environments own different contexts.

`reset()` normally resets/recompiles the feeder inside the owned context.

### 5.2 Capability discovery hierarchy

```text
Engine capabilities
        >=
Circuit capabilities
        >=
Problem-selected capabilities
```

This requires explicit discovery of the installed AltDSS/DSS engine surface and the loaded feeder's actual objects.

### 5.3 OpenDSS-native canonical addressing

Canonical identifiers:

```text
<Class>.<ObjectName>.<PropertyOrQuantity>
```

with selectors when required for terminal/phase/winding/etc.

### 5.4 Distinct registries

At minimum:

- `CapabilityRegistry`
- `CircuitRegistry`
- `StateRegistry`
- `ActionRegistry`
- `DisturbanceRegistry`
- `ConstraintRegistry`
- `ParameterRegistry`

A writable property is not automatically a controller action.

Mutable quantities are classified at least as:

- `READ_ONLY`
- `INIT_ONLY`
- `STEP_CONTROLLABLE`

### 5.5 Optional control problem

OpenDSSSim must run with `problem=None`.

Pure time-series simulation uses the same Gymnasium lifecycle with externally supplied profiles and configured native OpenDSS controls.

### 5.6 External snapshot time-series engine

OpenDSSSim owns time.

Do not use OpenDSS `Daily`, `Yearly`, or `Duty` as the authoritative time-series engine.

Each step:

1. select external profile sample;
2. write Load P/Q;
3. write PV/weather/exogenous inputs;
4. write external control request if present;
5. permit only configured native-control authority;
6. execute one authoritative snapshot solve;
7. validate convergence;
8. read realized controls/state;
9. evaluate problem/constraints/metrics if configured;
10. record;
11. advance OpenDSSSim clock.

### 5.7 Profile duration policy

At minimum:

- `strict`
- `tile`

Optional seeded noise is applied by the OpenDSSSim exogenous-data layer.

### 5.8 Control authority

At minimum:

- `NATIVE`
- `EXTERNAL`

`HYBRID` is deferred until exact coordination semantics are defined.

### 5.9 Generic action-resolution layers

OpenDSSSim should preserve three conceptually distinct layers where applicable:

1. **requested** — controller command;
2. **applied/admissible** — command after explicit validation/projection policy;
3. **realized** — actual post-solve physical/control value.

If the selected policy performs no projection, applied equals requested.

No silent rescue or clipping is allowed without an explicit policy and recorded flag.

### 5.10 Current-state surface

The complete solved-state capability surface is logically accessible.

Expensive quantities may be lazily extracted.

Controller observations are selected views, not the plant state itself.

### 5.11 Secondary history store

Always present at the interface, with configurable retention:

- H0 Minimal
- H1 Operational
- H2 Full State
- H3 Audit/Diagnostic

Future disk streaming may supplement memory for long runs.

### 5.12 Independent execution profiles

- FAST
- STANDARD
- AUDIT

Execution profile controls instrumentation cost, never physical simulation semantics.

### 5.13 Solution/convergence contract

Snapshot solve status, convergence, native-control iteration behavior, and errors require an explicit `SolutionResult`/equivalent contract.

### 5.14 Source identity before GitHub

Every qualified patch/run must include a deterministic source manifest and SHA256 because Git commit identity does not yet exist.

### 5.15 Future coupling-port contract

Plan but do not implement in A01:

- child simulator P/Q output;
- OpenDSS network-node attachment;
- `network_node_id`, `building_id`, `community_cluster_id`;
- simulator namespaces.

## 6. IMMUTABLE / REFERENCE-ONLY

Do not copy these SmartCommunitySim_2 contracts/science into OpenDSSSim:

- legacy `(2,39,N_House)` plant-state tensor;
- legacy `(1,13,N_House)` action tensor;
- MATLAB backend and MATLAB source tree;
- SmartCommunitySim house/community thermal physics;
- community energy-pooling equations;
- HVAC/battery/EV/PV community dispatch science;
- SmartCom benchmark house/device materialization;
- SmartCom-specific load/weather provenance assumptions;
- SmartCom MPC formulations/controller code;
- SmartCom RL controller science/reward tuning;
- SmartCom community metric formulas;
- thesis compatibility adapters;
- SmartCom pricing science;
- SmartCom visualization implementation;
- historical action-channel constants;
- community-specific `PlantBackend` method inventory.

They may be consulted to understand architectural intent or qualification patterns only.

## 7. Key Architectural Differences from SmartCommunitySim_2

### 7.1 OpenDSSSim plant state is discoverable, not fixed-width

SmartCommunitySim_2 preserves historical fixed tensors for compatibility.

OpenDSSSim instead exposes feeder-dependent state through native DSS object/property identities and structured registries.

### 7.2 OpenDSSSim does not have a mandatory control study

The simulator itself is useful for externally driven time-series power flow with native controls and no external controller.

### 7.3 OpenDSSSim history and execution cost are independent

SmartCommunitySim_2's modern `MINIMAL/STANDARD/DEBUG` recorder primarily controls retained runtime data.

OpenDSSSim separates:

```text
History detail: H0 / H1 / H2 / H3
Execution instrumentation: FAST / STANDARD / AUDIT
```

### 7.4 OpenDSSSim owns the time-series loop

The external profile layer is authoritative. AltDSS/OpenDSS solves one externally configured operating point per OpenDSSSim step.

### 7.5 OpenDSSSim needs explicit native-control ownership

OpenDSS control objects can alter the same devices as external controllers, requiring first-class control-authority semantics.

## 8. Proposed OpenDSSSim A01 Patch

**Patch working name:** `OpenDSSSim_A01_AltDSS_Foundation_Context_Snapshot_v01`

### A01 objective

Establish the smallest qualified executable OpenDSSSim foundation.

### A01 shall add

```text
pyproject.toml

src/opendsssim/
    __init__.py

    backends/
        __init__.py
        base.py
        altdss_backend.py
        factory.py

    network/
        __init__.py
        loading.py

    plant/
        __init__.py
        core.py
        solution.py

    environment/
        __init__.py
        simulator.py

    persistence/
        __init__.py
        schema.py
        manifest.py

tests/
    unit/
        backends/
        network/
        plant/
        environment/
        persistence/

    integration/
        test_altdss_context_isolation.py
        test_snapshot_solve.py
        test_reset_recompile.py

docs/development/patches/
    <A01_PATCH_ID>.md

scripts/validation/
    validate_a01.py
```

The exact final file list should be frozen immediately before patch construction.

### A01 functional contract

A01 must demonstrate:

1. package imports from `src/opendsssim`;
2. an `AltDSSBackend` can create and own one independent AltDSS context;
3. two environment instances receive distinct contexts;
4. a supplied DSS master file can be compiled/loaded;
5. one snapshot power-flow solve can be executed;
6. convergence/status is returned through a typed solution result;
7. `reset()` deterministically restores/recompiles the circuit;
8. environment close releases backend resources cleanly;
9. a run/source manifest can identify the package/patch/environment before GitHub exists;
10. targeted unit/integration validator passes.

### A01 may include only a minimal Gymnasium surface

A01 may establish `OpenDSSSimulator(gym.Env)` and lifecycle scaffolding, but it does **not** need the generalized observation/action registries yet.

### A01 non-goals

Do not implement in A01:

- capability discovery;
- full State/Action/Disturbance/Constraint registries;
- external load/PV/weather profile stepping;
- strict/tile/noise profile policy;
- full `ProblemSpec`;
- controller implementations;
- native-control authority;
- requested/applied/realized action framework;
- history H0–H3;
- FAST/STANDARD/AUDIT;
- PESGM IEEE-123 benchmark freeze;
- MPC;
- RL;
- Gurobi integration;
- visualization;
- BuildingsToGridSim coupling.

These belong to later patches.

## 9. Environment Boundary for A01

Current laptop environment already contains the existing DSS-Python stack but does not contain `altdss`.

A01 is the first stage where `altdss` becomes genuinely necessary.

Before installing A01:

1. capture the current `scalebridge-dev-gpu-laptop` environment state;
2. perform a dependency-impact dry run;
3. install only the minimum required `altdss` package if the impact remains additive;
4. do not install Gurobi for A01;
5. run AltDSS import/context/version smoke;
6. run existing environment regression/sanity checks sufficient to establish that the stable environment was not disturbed;
7. record before/after package state in the A01 patch documentation.

`gurobipy` remains deferred until the first optimization/MPC patch that genuinely requires it.

## 10. Ratification Decision

If ratified, this document becomes the architecture boundary for OpenDSSSim A01.

The next development action is:

```text
A01 prerequisite environment qualification
        ->
minimal additive AltDSS installation only when required
        ->
fresh OpenDSSSim tree
        ->
A01 patch construction
        ->
installer + validator + patch .md
        ->
laptop qualification
```
