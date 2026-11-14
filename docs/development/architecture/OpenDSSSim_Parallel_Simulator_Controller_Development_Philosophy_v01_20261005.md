# OpenDSSSim Parallel Simulator/Controller Development Philosophy

## 1. Document identity

- Document: `OpenDSSSim_Parallel_Simulator_Controller_Development_Philosophy_v01_20261005.md`
- Date: 2026-10-05
- Status: **FROZEN architectural contract**
- Parent project: OpenDSSSim / IEEE PES General Meeting 2027
- Predecessor software checkpoint: `OpenDSSSim_A01_AltDSS_Foundation_Context_Snapshot_v01R1_20261005`
- Predecessor qualified source-manifest SHA256: `3396BC748F3EF763934A4434A02160E81FB3E2B68C10B0C05E137105422C6CD4`

## 2. Purpose

OpenDSSSim is developed through two parallel but explicitly separated tracks:

1. **Simulator/plant track** — generalized electrical-plant execution and interfaces.
2. **Controller-science track** — literature-backed control formulations and generalized controller implementations.

Parallel development is permitted because the two tracks communicate only through frozen controller-independent contracts. Parallel work must never create a second plant API or allow controller code to bypass OpenDSSSim.

This document freezes the ownership boundary, synchronization points, controller-generalization semantics, and intended repository organization.

## 3. Non-negotiable plant/controller invariant

**Controllers never import, own, or manipulate AltDSS directly.**

Controller modules must not:

- import `altdss`;
- create or retain AltDSS contexts;
- issue DSS text commands to alter the physical circuit;
- write directly to AltDSS/OpenDSS objects;
- mutate backend objects behind the plant boundary.

The authoritative physical transition is owned by OpenDSSSim:

```text
controller
    |
    | requested action a_req
    v
OpenDSSSim action contract
    |
    | validation / admissibility / explicit projection policy
    v
a_applied
    |
    v
OpenDSSSim plant/backend
    |
    v
AltDSS snapshot solve
    |
    v
a_realized + next solved state
```

At the Gymnasium level, `env.step(...)` is the authoritative mutation boundary.

A controller may use controller-independent, **non-mutating** topology, forecast, parameter, constraint, or prediction services only when those services are explicitly exposed by a frozen OpenDSSSim contract.

## 4. Track ownership

### 4.1 Simulator/plant track owns

- AltDSS backend and context lifecycle;
- circuit loading and reset semantics;
- solution/convergence semantics;
- engine-capability discovery;
- circuit-capability discovery;
- native OpenDSS object identity and addressing;
- `CapabilityRegistry`;
- `CircuitRegistry`;
- `StateRegistry`;
- `ActionRegistry`;
- `DisturbanceRegistry`;
- `ConstraintRegistry`;
- `ParameterRegistry`;
- `ProblemSpec`;
- Gymnasium observation/action spaces;
- external episode clock;
- external load/PV/weather/event time-series execution;
- forecast exposure;
- control-authority semantics;
- requested/applied/realized action semantics;
- history levels;
- execution profiles;
- parity, deterministic replay, provenance, and qualification.

### 4.2 Controller-science track owns

- full-text literature audit;
- mathematical formulation of the six paper controllers;
- common physical-problem definitions for P1 and P2;
- controller capability requirements;
- controller objective/reward definitions;
- controller-specific solver or learning choices;
- controller diagnostics;
- controller tuning/training/calibration protocols;
- generalized controller source after science and simulator contracts are frozen;
- controller-specific unit tests that do not bypass the plant.

### 4.3 Shared decisions

The following must be ratified across both tracks before closed-loop paper campaigns:

- exact common physical action meaning;
- exact observation/information contract;
- forecast access;
- control interval;
- event/fault representation;
- physical bounds and constraints;
- unsupported-circuit semantics;
- paper metrics;
- controller configuration for the modified IEEE-123 experiment.

## 5. Meaning of a generalized controller

OpenDSSSim does **not** define generalized as “every controller runs on every OpenDSS file.”

The frozen definition is:

> A generalized controller implementation can instantiate on any compatible OpenDSS circuit that satisfies its declared capability requirements.

A controller declares requirements against generalized capabilities rather than fixed object names.

### 5.1 Volt/VAR + DER controller

Possible requirements include:

- solved bus-voltage observations;
- converged snapshot power flow;
- one or more externally controllable voltage/VAR resources;
- admissible physical bounds for those resources;
- optional forecast service for predictive control.

Compatible resources may include, as frozen later by control science:

- capacitors;
- regulator/transformer taps;
- DER/inverter reactive-power commands;
- storage active/reactive-power commands.

### 5.2 Restoration/reconfiguration controller

Possible requirements include:

- circuit topology;
- source connectivity;
- switchable branches;
- load/bus data;
- fault/outage representation;
- radiality/connectivity constraints;
- electrical-feasibility evaluation.

If a required capability is absent, controller construction or activation must return an explicit machine-readable **UNSUPPORTED** result. Silent degradation is prohibited.

## 6. Native OpenDSS vocabulary

OpenDSS classes and properties remain the canonical distribution-system vocabulary from circuit definition through observation, control, logging, and provenance.

Generalized controller code must not hard-code paper-feeder names such as a specific IEEE-123 capacitor, regulator, switch, or bus.

Paper-specific selections belong in experiment configuration, not generalized controller source.

## 7. Intended controller package organization

The following organization is frozen as architectural intent:

```text
src/opendsssim/controllers/
    __init__.py

    common/
        __init__.py
        base.py
        contracts.py
        capability_requirements.py
        registry.py
        results.py

    volt_var_der/
        __init__.py
        reference/
            __init__.py
            controller.py
            config.py
        optimization/
            __init__.py
            controller.py
            formulation.py
            config.py
        rl/
            __init__.py
            controller.py
            training.py
            policy.py
            config.py

    restoration/
        __init__.py
        reference/
            __init__.py
            controller.py
            graph_restoration.py
            config.py
        optimization/
            __init__.py
            controller.py
            formulation.py
            config.py
        rl/
            __init__.py
            controller.py
            training.py
            policy.py
            config.py
```

**A01D1 does not create these Python modules.** Their organization is documented now so that later implementation is coherent, but source creation waits for the required science and simulator contracts.

## 8. Controller-science documentation organization

The controller-science track lives under:

```text
docs/development/control_science/
    README.md
    P1_VoltVAR_DER_ControlScience_FROZEN.tex
    P2_Reconfiguration_Restoration_ControlScience_FROZEN.tex
    references/
        P1_reference_audit.md
        P2_reference_audit.md
```

The two `*_FROZEN.tex` files are the authoritative mathematical contracts for the six paper controllers.

Controller implementation must trace back to these documents through explicit `REUSE / ADAPT / NEW` records.

## 9. Intended common controller software contract

The exact Python API is not frozen by A01D1, but the semantic decomposition is:

### `ControllerRequirements`

Declares required:

- observation capabilities;
- action capabilities;
- topology/model services;
- forecast services;
- constraint services.

### `ControllerContext`

Provides only controller-authorized, controller-independent information:

- `ProblemSpec`;
- current observation;
- optional authorized state view;
- forecast view;
- non-mutating topology/model services;
- episode/time metadata.

### `ControllerOutput`

Contains:

- requested action `a_req`;
- diagnostics;
- solver/policy metadata;
- provenance.

A controller does not produce `a_applied` or `a_realized`.

## 10. Requested / applied / realized action ownership

The simulator owns three distinct layers:

1. `a_req` — controller request.
2. `a_applied` — action admitted by the plant contract after explicit validation/projection policy.
3. `a_realized` — control state physically realized after AltDSS solution and any permitted native-control interaction.

No controller may silently assume `a_req == a_realized`.

No clipping, projection, arbitration, or native-control override may be hidden.

## 11. MPC/optimization boundary

Optimization controllers may require a non-mutating model, network, forecast, or constraint service.

The optimization calculation does not own the physical plant.

For receding-horizon operation:

```text
current controller context
        |
        v
optimization / MPC solve
        |
        v
planned trajectory
        |
        v
first requested action only
        |
        v
env.step(a_req)
```

Future planned actions remain diagnostics/plans until requested in a later plant step.

## 12. RL generality boundary

The RL **implementation and training pipeline** can be circuit-general by deriving spaces and capability bindings from a compatible `ProblemSpec`.

A fixed-dimensional trained MLP/DQN/PPO checkpoint is not automatically transferable to arbitrary circuits with different observation/action dimensions.

For the PESGM experiment, the selected policy is trained and evaluated on the modified IEEE-123 case through the generalized OpenDSSSim interfaces.

Cross-feeder transferable graph/transformer policies are outside the present paper scope unless separately developed and validated.

## 13. Paper fairness invariant

Within a physical control problem, reference/rule, optimization/MPC, and RL controllers must share the same controller-independent plant specification:

- feeder and device population;
- episode time axis;
- disturbances;
- weather/load/PV trajectories;
- faults/events;
- controllable physical assets;
- action bounds;
- network constraints;
- initial conditions;
- control interval;
- common metrics.

Information privileges such as forecasts must be explicit per paradigm.

The paper evaluates controller portability and comparability through one plant abstraction; it does not claim algorithmic novelty for the six control methods.

## 14. Synchronization points

### A02 — Engine + circuit capability discovery

Controller track may state which generalized capability concepts it needs.

Simulator track owns discovery implementation and source-of-truth semantics.

### A03 — Seven registries

Controller track consumes frozen registry interfaces. It does not create competing registries.

### A04 — `ProblemSpec` + generalized Gymnasium spaces

This is the main controller/plant integration contract.

Generalized controller implementation should not bind to invented pre-A04 APIs.

### A05 — External time-series execution

Freezes disturbances, episode progression, and forecast exposure needed for fair control comparisons.

### Later stages

Control authority, requested/applied/realized actions, parity, replay, and campaign qualification must be frozen before final paper experiments.

## 15. Interface-request protocol

If controller science requires information or an operation that OpenDSSSim does not expose:

1. controller track documents the requirement;
2. simulator track evaluates whether it is controller-independent;
3. if accepted, the simulator track adds it through a qualified plant contract;
4. controller track consumes the frozen interface.

Direct AltDSS access is never the workaround.

## 16. Configuration separation

Generalized controller source contains no IEEE-123-specific object names.

Paper experiment configuration will later live separately, for example:

```text
configs/controllers/
    volt_var_der/
    restoration/
```

Configuration may select native circuit objects discovered by OpenDSSSim, but source algorithms remain circuit-general.

## 17. Dependency policy

A01D1 introduces no new dependency.

In particular:

- `gurobipy` remains deferred;
- no optimization solver is installed merely to freeze mathematics;
- RL environment packages are not changed;
- future dependency mutation requires its own preflight and qualification.

## 18. No-go rules

The following are prohibited:

- controller imports of `altdss`;
- controller-owned AltDSS contexts;
- controller DSS text mutation;
- hard-coded paper-feeder object names in generalized source;
- parallel controller-specific plant APIs;
- silent action clipping/projection;
- controller-defined realized actions;
- hidden forecast advantages;
- premature controller implementation before science freeze;
- premature controller binding before required simulator contracts are frozen;
- claiming a fixed RL checkpoint is universally feeder-transferable;
- claiming the six algorithms as OpenDSSSim algorithmic novelty.

## 19. Change control

This document is frozen at A01D1.

A later architecture patch may extend the controller contract, but it must:

- cite this document as predecessor;
- identify the exact changed invariant;
- preserve the plant/controller separation unless explicitly reopening the architecture;
- pass repository qualification.

## 20. Successor

After A01D1 qualification, plant development proceeds directly to:

**A02 — generalized engine and circuit capability discovery.**

Controller-science development proceeds independently through the literature-backed P1/P2 freeze documents and synchronizes again at the defined A02/A03/A04/A05 interfaces.
