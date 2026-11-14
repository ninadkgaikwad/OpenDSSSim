# OpenDSSSim A0 Architecture and PESGM 2027 Development Plan

**Document ID:** `OpenDSSSim_A0_Architecture_Development_Plan_v01R1_20260930`  
**Status:** RATIFIED ARCHITECTURE / DEVELOPMENT BASELINE  
**Date:** 2026-09-30  
**Intended repository path:** `docs/development/architecture/OpenDSSSim_A0_Architecture_Development_Plan_v01R1_20260930.md`

## 1. Purpose

OpenDSSSim will be a modern, generalized, AltDSS-backed Gymnasium simulator for distribution-system simulation, rule-based control, optimization, MPC, and reinforcement learning.

It is designed as a sibling of SmartCommunitySim_2 and, later, SmartBuildingsSim. These packages will eventually compose under BuildingsToGridSim. Each simulator must first mature independently and support its own publication before common refactoring.

The PESGM 2027 paper contribution is the generalized simulator architecture, not new controller science.

## 2. Simulator Family

| Simulator | Package | Domain |
|---|---|---|
| SmartComSim | `smartcommunitysim` | community DER / HEMS |
| SmartBuildingsSim | `smartbuildingssim` | building thermal / HVAC / DER |
| OpenDSSSim | `opendsssim` | electric distribution network |
| BuildingsToGridSim | `buildingstogridsim` | quasi-static composition/co-simulation |

Shared architectural vocabulary:
Backend; Plant; Device; State; Observation; Requested Action; Realized Action; Disturbance; Constraint; Parameter; Problem; Controller; Episode; Forecast; Metric; Recorder; Manifest; Coupling Port.

Domain-specific vocabulary remains native to the simulator. For OpenDSSSim, OpenDSS/AltDSS class and property names remain canonical wherever practical.


## 2A. Repository and Machine Governance

### Authoritative development repository

Create the clean local repository under:

```text
C:\Users\ninad\Dropbox\NinadGaikwad_PhD\Gaikwad_Research\Gaikwad_Research_Work\OpenDSSSim
```

or the final explicitly agreed clean repository folder name under the same `Gaikwad_Research_Work` root.

The repository is Dropbox-synchronized to Laptop, Lab PC, and Home PC.

### Frozen development-authority rule

**All source-code development occurs on the Laptop only.**

This includes source edits, package architecture, configuration/schema changes, installers, validators, development scripts, patch ZIP creation, patch Markdown records, source/hash manifests, controller implementation, science changes, and bug fixes that alter shared source.

Lab PC and Home PC are production/qualification execution machines only. They must not independently modify the shared repository source.

Because the repository is shared by Dropbox:
- Laptop/Lab PC/Home PC do not use Git to synchronize development source with one another;
- source propagation is by Dropbox synchronization;
- GitHub is deferred until after PESGM paper completion, repository cleanup, and detailed README/release preparation.

Before any production run on Lab PC or Home PC:
1. confirm Dropbox synchronization is complete;
2. verify authoritative source hashes/patch ID;
3. qualify the local Conda environment;
4. run the required machine smoke/validator;
5. only then launch the production campaign.

### Machine roles

| Machine | Role |
|---|---|
| **Laptop** | sole development authority; package/core development; controller implementation; integration; validation; rule-based runs; smaller campaigns; MPC/RL development and debugging |
| **Lab PC** | heavier MPC/optimization production runs and production qualification |
| **Home PC** | heavier RL training/production runs and production qualification |

No production-machine source hotfix is allowed. Any defect found on Lab PC or Home PC is corrected on the Laptop, repackaged as an explicit patch, Dropbox-synchronized, and then requalified.

### Conda environments

Use the machine-local ScaleBridge GPU environments:
- Laptop: `scalebridge-dev-gpu-laptop`
- Lab PC: `scalebridge-dev-gpu-labpc`
- Home PC: `scalebridge-dev-gpu-homepc`

Do not assume package parity between machines.

When a machine first enters OpenDSSSim execution, record the pre-change environment state, add only required dependencies, and capture the post-change qualification state.

At minimum record Python, Conda environment, AltDSS-Python, DSS engine, Gymnasium, NumPy, SciPy, RL stack where relevant, and optimization-solver versions where relevant.

### Gurobi requirement

At least one PESGM MPC/optimization workload is expected to be **mixed-integer**.

Gurobi is therefore an approved required dependency for that workload. Valid Gurobi licenses are available on Laptop and Lab PC.

Laptop is used for development and qualification of the mixed-integer MPC implementation. Lab PC is used for heavier mixed-integer MPC production runs.

Every Gurobi-dependent machine qualification must record the Gurobi package/version, license availability, one minimal solver smoke test, and one OpenDSSSim MPC integration smoke before production.

## 3. Core Architecture

```text
                      CONTROLLERS
             Rule / Optimization / MPC / RL
                          |
                          v
                    Gymnasium API
                  reset() / step()
                          |
                          v
                 OpenDSSSimulator
                  /             \
             ProblemSpec     EpisodeRuntime
                  \             /
                   \           /
                    OpenDSSPlant
             /          |          \
      State/Signal   Actions     Constraints
        Registry     Registry      Registry
             \          |          /
                   AltDSSBackend
                         |
                   AltDSS Context
                         |
                    DSS Circuit
```

**Invariant:** controllers do not directly mutate AltDSS during an experiment. Real plant transitions occur through the Gymnasium environment.

## 4. Control Problem Is Optional

OpenDSSSim must run as a simulator even when no external control problem is defined.

Supported modes:
1. Native/no-external-control simulation
2. Rule-based control
3. Optimization
4. MPC
5. RL
6. Later DMPC/MARL through higher-level adapters

A no-control environment may expose a Gymnasium no-op action while configured native OpenDSS controls operate.

```python
env = OpenDSSSimulator(
    network="...",
    problem=None,
    control_authority="native",
)
```

The normal Gymnasium lifecycle remains authoritative:

```python
obs, info = env.reset(seed=seed)
obs, reward, terminated, truncated, info = env.step(noop_action)
```

A convenience episode runner may call `step()` internally but must not bypass it.

## 5. External Time-Series Simulation Contract

OpenDSSSim does **not** use OpenDSS `Daily`, `Yearly`, or `Duty` modes as its authoritative time-series engine.

Every simulation step is an externally orchestrated snapshot power-flow transition.

At each step:

1. Read the external time-series sample for the current OpenDSSSim clock.
2. Apply user-supplied load inputs.
3. Apply user-supplied PV/weather inputs.
4. Apply configured exogenous inputs/events.
5. Apply the external requested control action, if any.
6. Allow only native OpenDSS controls whose authority is configured as native.
7. Execute one authoritative snapshot power-flow solve call.
8. Verify convergence.
9. Read realized controls and required plant state.
10. Evaluate configured constraints/metrics/reward.
11. Record the transition.
12. Advance the OpenDSSSim episode clock.

OpenDSS may perform its normal internal iterative solution/control processing during that solve, but OpenDSSSim owns time advancement.

Required user-supplied exogenous channels include:
- load active power;
- load reactive power or power-factor-derived reactive power;
- PV irradiance;
- PV temperature when used by the chosen PV model;
- optional additional weather channels;
- faults/topology availability/events;
- later price/market signals where needed.

Signals may be global, class-wide, per-device, per-phase, or per-node/object.

### Arbitrary duration

Episode length is independent of source-series length.

Required policies:
- `strict`: fail if the requested episode exceeds supplied data;
- `tile`: repeat the supplied sequence periodically.

### Deterministic noise

Noise injection is optional, first-class, and seed-controlled.

Possible modes:
- additive;
- multiplicative;
- Gaussian;
- bounded uniform;
- user-defined callable/model.

Run manifests record source data, tiling policy, noise model, noise parameters, and seed.

## 6. Package Organization

```text
src/opendsssim/
    backends/
        base.py
        altdss_backend.py
        factory.py

    network/
        catalog.py
        loading.py
        materialization.py
        normalization.py
        provenance.py

    devices/
        contracts.py
        discovery.py
        registry.py
        capabilities.py
        naming.py

    disturbances/
        core.py
        profiles.py
        events.py
        noise.py

    initialization/
        core.py

    plant/
        core.py
        solution.py
        controls.py
        topology.py
        snapshot.py

    controller_runtime/
        schemas.py
        context.py
        actions.py
        episode.py
        forecast.py
        constraints.py
        device_map.py
        recording.py

    problems/
        schema.py
        registry.py
        builder.py

    environment/
        simulator.py
        spaces.py
        wrappers.py

    controllers/
        core.py
        native.py
        rule_based.py

    data/
    parameters/
    pricing/
    preprocessing/

    performance/
        core.py
        registry.py

    persistence/
        core.py
        schema.py
        manifest.py

    visualization/
        core.py
        network.py
        trajectories.py
        performance.py
        publication.py
```

Paper-specific controller implementations live outside the reusable package:

```text
experiments/pesgm2027/
    ieee123/
    volt_var/
        rule/
        mpc/
        rl/
    reconfiguration/
        rule/
        mpc/
        rl/
```

## 7. Registries

OpenDSSSim uses distinct registries:

- `CapabilityRegistry`: capabilities exposed by the installed AltDSS/DSS engine.
- `CircuitRegistry`: objects actually present in the loaded circuit.
- `StateRegistry`: readable operational quantities.
- `ActionRegistry`: qualified step-time controls.
- `DisturbanceRegistry`: exogenous runtime quantities.
- `ConstraintRegistry`: physical/operational limits.
- `ParameterRegistry`: configuration/init-only quantities.

A writable AltDSS property is not automatically a control action.

Mutable quantities are classified at minimum as:
- `READ_ONLY`
- `INIT_ONLY`
- `STEP_CONTROLLABLE`

## 8. Discovery Hierarchy

```text
Engine capabilities
        >=
Circuit capabilities
        >=
Problem-selected capabilities
```

Engine discovery asks what the current AltDSS/DSS release supports.

Circuit discovery asks what exists in this feeder.

Problem selection chooses the state, observation, action, disturbance, forecast, objective, and constraint subsets required by one study.

Problem definitions must not modify plant physics.

## 9. Canonical OpenDSS Vocabulary

Canonical serialized identifiers use:

```text
<Class>.<ObjectName>.<PropertyOrQuantity>
```

Examples:

```text
PVSystem.PV1.kvar
Storage.BESS1.kW
Transformer.Reg1.Tap
Capacitor.Cap1.States
SwtControl.SW1.State
RegControl.Reg1.VReg
```

Selectors may extend the address:

```text
Transformer.XF1.Tap[Wdg=2]
Line.L1.TotalPowers[Terminal=1]
```

The underlying object/property vocabulary remains OpenDSS/AltDSS-native.

## 10. Observation and Action Views

Plant state and controller observation are distinct.

```text
Plant state  = complete available solved physical state
Observation  = problem/controller-selected view
Action space = problem/controller-selected subset of qualified controls
```

The preferred canonical Gymnasium representation is structured `Dict` spaces.

Flattening, normalization, compression, or encoding occurs through wrappers/adapters.

Custom user definitions must be supported without editing plant physics.

## 11. Current State and Secondary History Store

OpenDSSSim exposes two distinct concepts.

### 11.1 Current solved-state access

`env.state` (or equivalent) accesses the current solved plant state.

The complete capability surface is logically available. Expensive quantities may be lazily evaluated so fast control loops do not need to extract every AltDSS quantity on every step.

### 11.2 Secondary append-only history

`env.history` (or equivalent) always exists and grows with the episode according to a configurable history level.

Proposed levels:

- **H0 Minimal:** clock, convergence status, action summary, selected observation, reward/termination.
- **H1 Operational:** H0 plus selected operational states, constraints, main network metrics, disturbances.
- **H2 Full State:** H1 plus all qualified full-state operational quantities marked recordable by `StateRegistry`.
- **H3 Audit/Diagnostic:** H2 plus expensive element-level arrays, solver/control diagnostics, and qualification-only information.

History level never changes physical simulation results.

Disk streaming may later supplement append-only in-memory storage.

## 12. Execution/Complexity Profiles

History level and execution profile are independent.

### FAST
- one authoritative snapshot solve;
- minimum convergence checks;
- extract required observations/actions and mandatory runtime quantities;
- avoid expensive full-network diagnostics unless requested.

### STANDARD
- FAST behavior;
- requested/realized action capture;
- configured constraint checks;
- standard performance metrics;
- normal persistence instrumentation.

### AUDIT
- STANDARD behavior;
- full state/capability extraction needed for qualification;
- detailed native-control diagnostics;
- detailed parity/constraint instrumentation.

Execution profile may change instrumentation cost but never:
- exogenous samples;
- requested actions;
- control authority;
- physical limits;
- power-flow physics.

## 13. Requested vs. Realized Actions

Every controlled transition distinguishes:
- requested action;
- realized action.

Record:
- requested action;
- realized action;
- requested-realized difference;
- clipping/projection/constraint flags;
- control-authority source;
- relevant native-control changes.

No silent controller rescue is allowed unless explicitly defined by the selected action-realization policy.

## 14. Control Authority

Each controllable object/control relationship has explicit authority:

- `NATIVE`
- `EXTERNAL`

A future version may add `HYBRID`.

This prevents conflicts such as an external tap command followed by an active `RegControl` changing the same device.

Control authority is part of experiment configuration and the run manifest.

## 15. AltDSS Context Lifecycle

One instantiated Gymnasium/OpenDSSSim environment owns one independent AltDSS context.

```text
OpenDSSSimulator A -> AltDSS Context A
OpenDSSSimulator B -> AltDSS Context B
```

Creating a new environment creates a new context.

`reset()` normally resets/recompiles/restores the circuit deterministically inside the same owned context rather than creating a new context every episode.

A hard-reset/recreate operation may be available for testing.

Vectorized environments therefore contain multiple environment instances, each with its own AltDSS context.

## 16. Future BuildingsToGridSim v1 Coupling

BuildingsToGridSim v1 is quasi-static and uses one-way building/community-to-grid coupling during each outer step.

SmartComSim and SmartBuildingsSim child environments can run independently and in parallel. There may be many child instances attached to different OpenDSS nodes.

Outer-step order:

```text
1. Advance the common outer clock.
2. Supply exogenous inputs to child environments.
3. Run SmartComSim children in parallel.
4. Run SmartBuildingsSim children in parallel.
5. Each child exposes realized P/Q.
6. Aggregate P/Q by assigned OpenDSS network node.
7. Write aggregated P/Q into OpenDSSSim.
8. OpenDSSSim executes one quasi-static snapshot power flow.
9. Record global metrics/state.
10. Advance to the next outer step.
```

For BuildingsToGridSim v1:
- SmartComSim exposes P/Q;
- SmartBuildingsSim exposes P/Q;
- OpenDSSSim consumes those injections/loads;
- V/f feedback from OpenDSSSim to SmartComSim/SmartBuildingsSim is not required.

Bidirectional voltage-sensitive iterative coupling is future work.

## 17. Coupling Ports and IDs

Each simulator should later expose a `CouplingPortRegistry`.

For v1 the essential child electrical outputs are:

```text
electrical.P
electrical.Q
```

BuildingsToGridSim supplies composition-level IDs:
- `network_node_id`
- `building_id`
- `community_cluster_id`

Composite names are globally namespaced, for example:

```text
OpenDSSSim::PVSystem.PV1.kvar
SmartBuildingsSim::Building.B17.Zone.Z1.Temperature
SmartComSim::CommunityCluster.C03.Storage.SOC
```

Child simulators retain local vocabulary internally.

## 18. Refactoring Policy

Do not refactor SmartCommunitySim_2 into a shared framework during PESGM development.

Each simulator first succeeds independently and supports its own planned paper.

Only after SmartComSim, OpenDSSSim, and SmartBuildingsSim are mature should common abstractions be extracted into a BuildingsToGridSim/shared-core library.

## 19. PESGM 2027 Experimental Scope

Use one literature-derived modified IEEE 123-bus feeder and two control problems.

### P1 — Volt/VAR / DER regulation
- Rule/native control
- MPC/optimization
- RL

### P2 — Network reconfiguration/restoration
- deterministic rule/heuristic
- MPC/optimization
- RL

Total:

```text
2 control problems x 3 controller paradigms = 6 application scenarios
```

The six scenarios are validation workloads, not algorithmic contributions.

Framework qualification additionally includes:
- automatic capability discovery;
- direct AltDSS/Gymnasium parity;
- deterministic replay.

## 20. PESGM Reference Baseline Set

### Base feeder
Use the established IEEE/OpenDSS IEEE 123-bus feeder as the physical starting point.

### P1 setup / RL anchor
T.-H. Fan, X. Y. Lee, and Y. Wang, **“PowerGym: A Reinforcement Learning Environment for Volt-Var Control in Power Distribution Systems,”** L4DC 2022.

Use as the primary public reference for:
- IEEE-123 VVC benchmark structure;
- capacitor/regulator/storage action semantics;
- VVC objective/reward concepts;
- reference RL behavior;
- public modified 123-bus assets where suitable.

PowerGym's public 123Bus benchmark contains 4 capacitors, 7 regulators, and 4 batteries.

For schedule safety, prefer an established algorithm already demonstrated by PowerGym that is easy to reproduce in the final selected action space. PPO is the default low-risk choice unless a later source/code audit shows SAC can be reproduced without adding custom algorithm work.

### P1 MPC anchor
D. Erazo-Caicedo, E. Mojica-Nava, and J. Revelo-Fuelagán, **“Model predictive control for optimal power flow in grid-connected unbalanced microgrids,”** Electric Power Systems Research, vol. 209, 108000, 2022. DOI: `10.1016/j.epsr.2022.108000`.

Use as the main reference for:
- receding-horizon MPC/OPF;
- unbalanced IEEE-123 validation;
- renewable generation;
- storage;
- voltage regulators;
- tap transformers;
- capacitor-bank control;
- forecasting.

For PESGM, use only controls present in the frozen P1 benchmark. Do not introduce new MPC science.

### P1 rule/native anchor
Use PowerGym's native-DSS-control comparison mode plus the official IEEE-123/OpenDSS regulator/control definitions.

No new rule-controller science is required.

### P2 problem/MPC anchor
W. Liu, F. Ding, and C. Zhao, **“Dynamic Distribution System Restoration Strategy for Resilience Enhancement,”** IEEE ISGT 2020.

Use as the primary reference for:
- modified IEEE-123 restoration/reconfiguration;
- dynamic topology adjustment;
- DER-aware restoration;
- MPC/receding-horizon topology and DER-setpoint updates;
- forecast-driven sequential operation.

A source-audit step must extract exact network modifications, switch set, DER locations, disturbances, objectives, constraints, and time discretization before implementation.

### P2 RL anchor
S. H. Oh, Y. T. Yoon, and S. W. Kim, **“Online reconfiguration scheme of self-sufficient distribution network based on a reinforcement learning approach,”** Applied Energy, vol. 280, 115900, 2020. DOI: `10.1016/j.apenergy.2020.115900`.

Use as the primary RL reference for:
- IEEE-123 online reconfiguration;
- DQN topology decisions;
- voltage/loading security;
- switching penalties;
- variable renewable/load conditions.

### P2 rule/heuristic anchor
Use a published IEEE-123 graph/heuristic restoration baseline, with **“Distribution system restoration using graph theory after multiple faults”** (IET Energy Systems Integration, 2020) as the primary candidate.

Use for:
- graph-based restoration logic;
- switching;
- load prioritization/curtailment;
- modified IEEE-123 validation.

The P2 rule controller is a referenced deterministic baseline, not a new algorithm.

### Reference adaptation rule

Freeze each physical problem first.

Then adapt each referenced controller only as necessary to consume the same OpenDSSSim observation/action contract and the same physical benchmark.

Every deviation from the source paper must appear in an experiment provenance table.

## 21. Patch Documentation Contract

Every development patch installs its own Markdown record:

```text
docs/development/patches/<PATCH_ID>.md
```

Each patch document must contain:
1. Patch ID/date
2. Development stage
3. Objective
4. Authoritative predecessor
5. Input files/bundles inspected
6. Architecture/science decisions
7. Files added/modified
8. Explicit non-goals
9. Public API changes
10. Configuration/schema changes
11. Tests/validators added
12. Installer command
13. Validation command
14. Expected pass markers
15. Rollback notes
16. Known limitations
17. Next-stage entry criteria

Repository-tree and directed-input-bundle collectors must include these Markdown records automatically so later development receives the full decision history.

## 22. Development Workflow

Before every patch:

1. Generate fresh repository tree.
2. Inspect latest architecture/freeze/patch Markdown records.
3. Request a narrow directed input bundle.
4. Inspect source, tests, schemas, configs, and predecessor contracts.
5. Freeze a `REUSE / ADAPT / NEW / IMMUTABLE` decision table.
6. Build patch ZIP.
7. Include installer.
8. Include validator.
9. Include patch Markdown record.
10. Run targeted qualification.
11. Run shared-core regression if applicable.
12. Freeze qualification evidence before continuing.

Windows workflows are PowerShell-first and run from repository root unless stated otherwise.


## 22A. Pre-Git Source Identity

Until the post-paper GitHub release is created, Git commit IDs are not the authoritative source identity.

Every patch qualification and production campaign should identify the code state using package version, architecture document ID, latest qualified patch ID, source manifest SHA256, relevant immutable/freeze hashes, machine role, Conda environment manifest, AltDSS/DSS versions, and solver/runtime versions where applicable.

After the PESGM paper is complete, the frozen paper source state should be imported into the cleaned GitHub repository and mapped to an authoritative release commit/tag.

## 23. Four-Week Implementation and Results Plan

PESGM 2027 full-paper deadline: **2026-11-10**.

### Initial architecture/bootstrap — 2026-09-30 to 2026-10-01
Target:
- A0 architecture freeze;
- SmartCommunitySim_2 architectural reference collection;
- clean local Dropbox-synced OpenDSSSim repository bootstrap if practical;
- initial environment/dependency audit.

### Vacation — 2026-10-02 to 2026-10-04
**No development work planned.**

### Week 1 effective development — 2026-10-05 to 2026-10-10
**Generalized simulator foundation**

Target:
- package/repository skeleton;
- AltDSS backend/context ownership;
- circuit loading;
- engine/circuit discovery;
- canonical naming;
- initial registries;
- no-control snapshot simulation;
- external load/PV/weather time series.

Exit:
- arbitrary IEEE feeder loads;
- externally supplied profiles drive repeated snapshot solves;
- strict/tile semantics pass;
- independent environment contexts pass.

### Week 2 — 2026-10-11 to 2026-10-17
**Gymnasium + runtime + reproducibility**

Target:
- Gymnasium reset/step;
- structured spaces;
- user-defined observation/action selection;
- ProblemSpec;
- requested/realized actions;
- control authority;
- episode runtime;
- seeded noise;
- history levels;
- FAST/STANDARD/AUDIT;
- persistence/manifests;
- deterministic replay;
- AltDSS/Gym parity harness.

Exit:
- generalized plant framework feature-complete for the paper;
- discovery, replay, and parity qualification passing.

### Week 3 — 2026-10-18 to 2026-10-24
**Frozen IEEE-123 benchmark + P1**

Target:
- freeze literature-derived IEEE-123 benchmark;
- freeze P1 problem;
- implement reference native/rule baseline;
- implement reference MPC;
- implement reference RL;
- qualify campaign;
- produce P1 results.

Exit:
- S1/S2/S3 use the identical OpenDSSSim plant.

### Week 4 — 2026-10-25 to 2026-10-28
**P2 + paper campaigns**

Target:
- freeze P2 network/problem;
- implement referenced heuristic;
- implement referenced MPC;
- implement referenced RL;
- complete S4/S5/S6;
- complete capability table;
- complete parity/replay results;
- freeze paper result artifacts.

Exit:
- six application scenarios complete;
- framework qualification complete;
- figures/tables/result CSVs frozen by about 2026-10-28.

## 24. Paper Week and Submission Buffer

### Paper week — 2026-10-29 to 2026-11-05
- finalize figures;
- finalize state-of-art comparison;
- write five-page PESGM manuscript;
- verify novelty claims;
- verify controller/setup provenance;
- finalize reproducibility description.

### Buffer — 2026-11-06 to 2026-11-09
Use for:
- failed-result repair;
- internal reviewer-style audit;
- formatting;
- references;
- PDF checks;
- author review;
- submission readiness.

### Submission — 2026-11-10

Do not plan new simulator features or controller science during paper week/buffer.

## 25. PESGM Scope Protection

Defer from v1:
- PettingZoo/MARL;
- DMPC;
- BuildingsToGridSim implementation;
- V/f feedback to building/community children;
- HELICS;
- cyber simulation;
- novel control algorithms;
- novel MPC mathematics;
- novel RL algorithms;
- shared-core refactor across simulator families.

The paper remains:

```text
one generalized AltDSS-backed Gymnasium plant
+
automatic native-DSS capability discovery
+
external time-series snapshot orchestration
+
two distinct reference control problems
+
three established controller paradigms
+
parity and deterministic replay
```

## 26. Architecture Invariants

1. Gymnasium is the canonical external plant boundary.
2. AltDSS is the primary backend.
3. One environment instance owns one independent AltDSS context.
4. OpenDSSSim owns simulation time.
5. Every step explicitly writes user/runtime exogenous quantities.
6. Every step executes one authoritative snapshot power-flow solve.
7. Native controls operate only under explicit control authority.
8. Physical plant and control problem are separable.
9. A control problem is optional.
10. Plant state and controller observation are separable.
11. Native DSS vocabulary is preserved.
12. User observation/action definitions do not alter plant physics.
13. Requested and realized actions are distinct.
14. Current-state access and history recording are distinct.
15. History detail and runtime-complexity profile are independent.
16. Execution profiles change instrumentation cost, not physics.
17. Paper controllers are external validation workloads.
18. SmartComSim/OpenDSSSim/SmartBuildingsSim are not prematurely merged.
19. BuildingsToGridSim v1 runs child building/community simulations in parallel, aggregates P/Q, then performs one quasi-static OpenDSS solve.
20. BuildingsToGridSim v1 does not require V/f feedback to child building/community simulators.
21. Every patch installs a permanent Markdown development record.
22. Fresh tree + directed input bundle + REUSE/ADAPT/NEW/IMMUTABLE analysis precedes every implementation patch.
23. The Laptop is the sole source-development authority.
24. Lab PC and Home PC are production/qualification execution machines only.
25. The shared repository is synchronized among the three local machines through Dropbox, not Git.
26. Gurobi is an approved required dependency for mixed-integer MPC; licensed Laptop and Lab PC installations are the authoritative Gurobi execution machines.
27. Production-machine defects are corrected through Laptop-authored patches; no source hotfixes are made directly on Lab PC/Home PC.

## 27. Immediate Next Step

Begin A0/A1 by collecting a fresh SmartCommunitySim_2 architectural reference bundle containing only the files needed to establish organization and contracts, then create the OpenDSSSim repository/package skeleton.

The first OpenDSSSim patch must not implement paper controller science.

Its purpose is:
- package organization;
- configuration/schema foundation;
- AltDSS backend;
- environment/context lifecycle;
- first snapshot solve;
- documentation and validation skeleton.
