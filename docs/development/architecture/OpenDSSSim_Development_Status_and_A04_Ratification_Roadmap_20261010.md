# OpenDSSSim Development Status and A04 Ratification Roadmap

**Date:** 2026-10-10  
**Status:** PRE-A04 planning record  
**Runtime implementation authorized by this document:** No

## Current Position

OpenDSSSim has completed the generalized plant foundation through persistent semantic registries. The project is now transitioning from generalized plant semantics to problem-specific Gymnasium interface construction.

Authoritative PRE-A04 identities:

- Frozen A03 patch: `OpenDSSSim_A03_Persistent_Seven_Semantic_Registries_v01R4_20261010`
- A03 qualified source-manifest SHA256: `97E1E9D935BA0BC81AE32D773E0AF25A23DB9FF7213295FBDB9F7CAF42AC2415`
- A03 semantic-policy SHA256: `51062A587FF88E8B33A1CA2F6BA57B182D58AF8A83A16EE8D0CA0F7D072A98E3`
- Qualified controller-science overlay: `OpenDSSSim_ControllerScience_Day2_P1_FullMathContract_v01R1_20261010`
- PRE-A04 composite repository files: `113`
- PRE-A04 composite source-manifest SHA256: `E20FD5B1C790BB51700205EAEB4832606D0140CE41A13512F65486A895FDE709`

The PRE-A04 A04 design directed-input collection passed, including the genuine A03 semantic/Gym surface probe.

## Completed Stages

| Stage | Purpose | Status |
|---|---|---|
| PRE-A01 / A0 | Architecture, repository organization, reuse/adapt/new planning | FINAL/FROZEN |
| A01 | AltDSS foundation, independent contexts, solve/reset/step lifecycle, Gym shell | FINAL/FROZEN |
| A01D1 | Simulator/controller packaging and documentation structure | FINAL/FROZEN |
| A02 | Generalized circuit/engine/capability discovery | FINAL/FROZEN |
| A02H1 | Persistent circuit inventory and native-control discovery | FINAL/FROZEN |
| A03D1 | Seven-registry semantic design/documentation freeze | FINAL/FROZEN |
| A03 | Persistent seven semantic registries and semantic compiler | FINAL/FROZEN |
| P1 Day-2 controller science | Full P1 Volt/VAR + DER mathematics | MATHEMATICS RATIFIED; RUNTIME NOT AUTHORIZED |
| PRE-A04 composite reconciliation | Frozen A03 + qualified P1 Day-2 overlay | QUALIFIED |
| PRE-A04 design directed input | Evidence bundle for ProblemSpec/Gym Dict design | PASS |

## Meaning of A01 Through A03

```text
OpenDSS / AltDSS
       |
       v
A01: physical simulator lifecycle
       |
       v
A02: discover what physically exists
       |
       v
A02H1: persist physical inventory and native controls
       |
       v
A03: assign semantic meaning
       |
       +--> CircuitRegistry
       +--> StateRegistry
       +--> ActionRegistry
       +--> DisturbanceRegistry
       +--> ConstraintRegistry
       +--> ParameterRegistry
       +--> CapabilityRegistry
       |
       v
A04: select what a particular control problem uses
```

Frozen architectural separation:

- `StateRegistry` is the plant-wide semantic catalog, not itself a controller observation space.
- `ActionRegistry` is the plant-wide legitimate external-command catalog, not itself every problem's action space.
- Writable OpenDSS property does not imply action authority.
- Native-control capability does not imply external-control authority.
- Problem-specific Gym spaces are derived from A03 semantics rather than hard-coded into A03.

## A04 Ratification Sequence

A04 is fully designed and ratified before runtime/source implementation.

### A04.1 — ProblemSpec Core Contract
Ratify what a `ProblemSpec` is, what A03 semantics it may select, what it may not redefine, deterministic identity/reproducibility, and the generalized-plant/problem boundary.

### A04.2 — Observation / State Selection
Ratify explicit semantic IDs, registry selectors/queries, ordered groups, deterministic ordering, and raw registered plant state versus controller observation.

### A04.3 — Action Selection
Ratify authorized A03 actions, discrete/continuous action representation, requested-action schema, unsupported/invalid behavior, and the prohibition on arbitrary writable-property control.

### A04.4 — Gymnasium `spaces.Dict` Compilation
Ratify compilation rules for `Box`, `Discrete`, `MultiDiscrete`, `MultiBinary`, `Dict`, shapes, dtypes, bounds, grouping, deterministic ordering, and identity.

### A04.5 — Constraints and Control Authority
Ratify intrinsic plant/device constraints versus problem-level operating constraints, native/external authority, compatibility, and machine-readable `UNSUPPORTED` diagnostics.

### A04.6 — Derived Observations and Wrappers
Ratify canonical raw observations versus derived features and keep flattening, normalization, scaling, and tensor conversion outside the canonical plant contract.

### A04.7 — Runtime Binding and Qualification Contract
Ratify semantic-address-to-observation binding, requested-action validation/application, requested/applied/realized boundaries, deterministic reproducibility, compatibility behavior, and representative generalized qualification cases.

## A04 Workflow Rule

```text
A04.1 ratify
  |
  v
A04.2 ratify
  |
  v
...
  |
  v
A04.7 ratify
  |
  v
incorporate all review changes
  |
  v
one complete A04 documentation patch
  |
  v
independent documentation qualification / freeze
  |
  v
fresh repo tree + implementation-directed input bundle
  |
  v
A04 source implementation
  |
  v
A04 implementation qualification / freeze
```

No A04 runtime implementation is authorized before A04.1 through A04.7 are ratified and the complete A04 documentation contract is independently qualified.

## Remaining Generalized OpenDSSSim Work

### A04 — ProblemSpec + problem-specific Gym Dict spaces
Current next stage.

### A05 — Exogenous Disturbance / Time-Series / Forecast Framework
Generalized load/PV/weather/exogenous profiles, forecast access, time alignment, and reproducible episode slicing.

### Later generalized runtime layers
Exact numbering remains unfrozen. Logical work includes registry-bound observation extraction, validated action application, requested/applied/realized histories, episode execution, logging, reproducibility, and compatibility/qualification surfaces.

## IEEE-123 Experimental Realization

After generalized infrastructure is sufficiently complete:

- modified IEEE 123-bus feeder;
- canonical OpenDSS object mapping;
- controllable-device selection;
- P1 `ProblemSpec`;
- P2 `ProblemSpec`;
- common disturbance/time-series realization.

Generalized OpenDSSSim source must not hard-code IEEE-123 object identities.

## P1 — Volt/VAR + DER Coordination

P1 mathematics is ratified. Remaining before experiment freeze:

- IEEE-123 mapping;
- fixed objective weights;
- RL training protocol;
- LinDistFlow validation.

Controller paradigms:

- rule-based/reference;
- optimization/MPC-style;
- reinforcement learning.

All use the same P1 `ProblemSpec` and plant boundary.

## P2 — Feeder Reconfiguration / Restoration

P2 follows the same plant/problem/controller separation and uses:

- rule/reference;
- optimization;
- reinforcement learning.

P2 must not require problem-specific mutation of the generalized simulator merely because its actions involve switching/reconfiguration.

## PESGM 2027 Experimental Matrix

| Problem | Rule / Reference | Optimization | RL |
|---|---:|---:|---:|
| P1 Volt/VAR + DER coordination | Yes | Yes | Yes |
| P2 Reconfiguration / restoration | Yes | Yes | Yes |

Native/no-control/baseline cases are included where scientifically appropriate.

> One feeder. One plant. One vocabulary. One interaction contract. Multiple control problems and paradigms.

## Production and Paper Completion

Remaining final work includes:

- baseline/native-control runs;
- six principal controlled scenarios;
- repeated scenarios/seeds/profiles as required;
- feasibility/convergence analysis;
- runtime/computational statistics;
- physical/control metrics;
- cross-controller comparisons;
- figures/tables;
- results/discussion;
- final PESGM 2027 manuscript.

## High-Level Development Arc

```text
PHASE I — GENERALIZED PLANT FOUNDATION
A0 / PRE-A01                                    COMPLETE
A01 AltDSS/Gym foundation                       COMPLETE
A02 physical discovery                          COMPLETE
A02H1 persistent inventory                      COMPLETE
A03 semantic registries                         COMPLETE

PHASE II — GENERALIZED PROBLEM INTERFACE
A04 ProblemSpec + Gym Dict spaces               NEXT
A05 exogenous/time-series/forecast               REMAINING
later runtime/history/qualification layers       REMAINING

PHASE III — FEEDER + PROBLEM INSTANTIATION
modified IEEE-123 realization                    REMAINING
P1 ProblemSpec                                   REMAINING
P2 ProblemSpec                                   REMAINING

PHASE IV — CONTROLLERS
P1 rule/reference                               REMAINING
P1 optimization                                 REMAINING
P1 RL                                           REMAINING
P2 rule/reference                               REMAINING
P2 optimization                                 REMAINING
P2 RL                                           REMAINING

PHASE V — SCIENCE FREEZE
P1 remaining science items                       REMAINING
P2 corresponding science freeze                  REMAINING
common experiment protocol                       REMAINING

PHASE VI — PRODUCTION EXPERIMENTS
scenario production                              REMAINING
metrics/analysis                                 REMAINING
figures/tables                                   REMAINING

PHASE VII — PAPER
PESGM 2027 results/discussion                    REMAINING
final manuscript                                 REMAINING
```

## Next Session Boundary

The next design activity is **A04.1 — ProblemSpec Core Contract**.

That session is discussion and ratification only. A04 coding begins only after A04.1–A04.7 are ratified, user revisions are incorporated, and the complete A04 documentation patch is installed and independently qualified.
