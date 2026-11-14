# A03.1 — Scope and Boundaries

## 1. Stage question

A03 answers:

> **Given a valid A02H1 `CircuitInventory`, what semantic capabilities and channels does
> OpenDSSSim expose for generalized simulation/control infrastructure?**

A03 is a semantic compilation stage, not a controller stage and not a problem-selection
stage.

## 2. Predecessor

A03 depends on A02H1:

```text
DSS sources
   -> A01 load/solve
   -> A02 read-only physical discovery
   -> A02H1 persistent CircuitInventory
   -> A03 persistent semantic compilation
```

A03 must consume the valid inventory instead of reconstructing the physical circuit model
from scratch.

## 3. Outputs

A03 produces one deterministic `SemanticRegistryBundle` containing:

1. `CircuitRegistry`
2. `StateRegistry`
3. `ActionRegistry`
4. `DisturbanceRegistry`
5. `ConstraintRegistry`
6. `ParameterRegistry`
7. `CapabilityRegistry`

The bundle carries sufficient provenance to prove which physical inventory and semantic
policy generated it.

## 4. Core separations

### 4.1 Physical existence vs semantic meaning

A02/A02H1 discovers `PVSystem.PV1.kvar` exists. A03 decides whether that address is a
legitimate external reactive-power action, a parameter, a readout, or some combination
supported by explicit policy.

### 4.2 State vs observation

`StateRegistry` is the set of generalized plant-state/readout quantities OpenDSSSim knows
how to expose.

A future `ProblemSpec` selects a controller-authorized observation subset.

Therefore:

```text
StateRegistry != ObservationSpace
```

### 4.3 Action capability vs selected action space

`ActionRegistry` describes legitimate plant commands that OpenDSSSim may support.

A future `ProblemSpec` chooses the action subset for one problem.

Therefore:

```text
ActionRegistry != ProblemSpec action space
```

### 4.4 Intrinsic constraint vs operating requirement

A03 records intrinsic plant/device domains and ratings, for example tap bounds or inverter
rating metadata.

Problem-specific requirements such as P1's ratified `0.95 <= V <= 1.05 p.u.` band remain
outside A03 and are selected later by `ProblemSpec`.

### 4.5 Native control vs external control

The existence of `RegControl`, `CapControl`, `InvControl`, etc. creates native-control
capabilities and circuit relationships.

It does not grant an external MPC/RL controller authority over those settings or their
controlled devices.

## 5. Controller-science requirements carried into A03

The controller-science track requires:

- capability query;
- circuit/native-object registry;
- explicit unsupported semantics;
- future binding of generalized controllers to discovered compatible objects.

A03 supplies the registry/capability metadata needed for those later contracts.

It does not yet implement controller instantiation, `ProblemSpec`, forecasts, or final
requested-action schemas.

## 6. P1 boundary

The P1 physical problem currently ratifies concepts such as:

- bus/phase voltage information;
- regulator/tap state and control;
- capacitor state and control;
- PV active/reactive operating points;
- PV reactive control;
- load and PV-availability exogenous values;
- intrinsic inverter capability metadata.

A03 must expose generalized capabilities from which a later P1 `ProblemSpec` can select
its channels.

A03 must **not** hard-code:

- ten regulators;
- ten capacitors;
- ten PV channels;
- exact IEEE-123 object names;
- P1 objective weights;
- P1 final observation vector.

## 7. P2 boundary

The P2 controller-science scaffold requires future graph/topology quantities, switch
actions, source/connectivity information, outage/fault/event description, feasibility
information, and optional DER support.

A03 therefore must model generalized topology/readout and switch-command semantics, while
the exact P2 physical benchmark remains outside A03 until controller science freezes it.

## 8. Explicit non-goals

A03 does not implement:

- `ProblemSpec`;
- final Gym observation/action spaces;
- native/external/HYBRID control authority switching;
- disturbance time-series execution;
- forecast generation/view;
- reward/cost computation;
- requested/applied/realized action execution;
- controllers;
- MPC;
- RL;
- IEEE-123 experiment configuration;
- silent fallback when a required capability is absent.
