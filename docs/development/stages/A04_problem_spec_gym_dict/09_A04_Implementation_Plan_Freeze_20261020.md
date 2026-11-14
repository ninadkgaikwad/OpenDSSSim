# A04 Implementation Plan Freeze

**Date ratified:** 2026-10-20  
**Status:** RATIFIED IMPLEMENTATION PLAN  
**Runtime source implementation authorized by this document:** A04I1 only, after this plan patch is independently qualified  
**Whole-A04 documentation authority:** 153 files

## 1. Purpose

This document freezes the exact implementation decomposition for A04 after:

- A04.1 through A04.7 design ratification;
- whole-A04 documentation freeze;
- fresh 153-file repository tree;
- implementation-directed evidence collection and source inspection.

A04 implementation is deliberately staged into four independently qualified patches rather than one monolithic change.

## 2. Frozen Evidence Authority

The implementation plan is based on:

```text
Whole-A04 repository authority:
153 files

Whole-A04 qualified source-manifest SHA256:
5C05B4B441A47DF18B06617592FB3004CB9F598613E5A95365D5462A8CB23345

Implementation-directed evidence:
99 repository files

Directed-evidence ZIP SHA256:
EBC679C8A7E707A3781F02C9C0C53FF7741B2DE9894295347C7CEA9825FD490A
```

No source modification is permitted outside this frozen implementation plan without a new ratified plan revision.

## 3. A05 Boundary: Exogenous Profiles and Shapes Are Explicitly Deferred

A04 does **not** freeze the temporal/profile tensor shapes for:

- load profiles;
- outdoor temperature;
- irradiance;
- weather variables;
- PV availability;
- exogenous PV-driving profiles;
- forecast windows;
- forecast uncertainty/noise;
- episode-time indexing.

These are A05 responsibilities.

A04 may reference **current resolved disturbance channels** semantically where a ProblemSpec selects them, but it does not define their time-series storage shape or forecast-horizon structure.

In particular:

```text
A04:
current semantic disturbance value
        |
        v
optional controller-visible current quantity

A05:
profile source
time index
episode slicing
forecast horizon
future tensor shape
truth-vs-forecast contract
noise / uncertainty
```

Actual PV electrical state such as present P/Q remains ordinary semantic state where exposed by A03/A04.

PV availability or future PV-driving information belongs to A05.

This boundary prevents A04I1 from embedding assumptions such as:

```text
(H,)
(H,N)
(T,N)
(T,N,F)
```

for exogenous data before the A05 temporal contract is ratified.

## 4. Frozen REUSE / ADAPT / NEW / IMMUTABLE Classification

### IMMUTABLE

A04 implementation must not change the semantic meaning of the frozen A01-A03 layers merely to make A04 convenient.

The following are implementation-plan immutable unless a separately ratified compatibility defect is discovered:

```text
src/opendsssim/semantics/schema.py
src/opendsssim/semantics/compiler.py
src/opendsssim/semantics/policy.py

src/opendsssim/discovery/*
src/opendsssim/network/*

src/opendsssim/persistence/inventory.py
src/opendsssim/persistence/inventory_schema.py
src/opendsssim/persistence/semantic_registry.py

src/opendsssim/plant/solution.py
```

A04 executes the already-defined A03 semantic addresses rather than rewriting them.

### REUSE

A04 reuses:

- `CircuitSource`;
- `CircuitInventory`;
- `SemanticRegistryBundle`;
- A03 semantic IDs and deterministic persistence identities;
- `NativePropertyAddress`;
- `RuntimeReadoutAddress`;
- `RuntimeCommandAddress`;
- A02H1 native-control relationships;
- A01 persistent AltDSS context lifecycle;
- `SolutionResult`;
- existing atomic JSON persistence patterns;
- A03 semantic fixture;
- all A01-A03 regression tests.

### ADAPT

Targeted adaptation is permitted in:

```text
src/opendsssim/backends/base.py
src/opendsssim/backends/altdss_backend.py

src/opendsssim/plant/core.py

src/opendsssim/environment/simulator.py
src/opendsssim/environment/__init__.py

src/opendsssim/persistence/__init__.py

src/opendsssim/__init__.py

pyproject.toml
```

Adaptation must preserve predecessor behavior and APIs unless the A04 contract explicitly extends them.

### NEW

A04 adds:

```text
src/opendsssim/problem/
    __init__.py
    schema.py
    resolution.py
    spaces.py

src/opendsssim/runtime/
    __init__.py
    schema.py
    access.py
    binding.py
    history.py
    identity.py

src/opendsssim/persistence/
    preflight.py
```

and additive A04 tests/validation.

## 5. Frozen Problem-Layer Structure

### `problem/schema.py`

Contains immutable typed schemas for authored and resolved control problems, including conceptually:

```text
ProblemSpec
ResolvedProblemSpec

ObservationSpec
ResolvedObservationSpec

ActionSpec
ResolvedActionSpec

ExactSemanticRef
SemanticQuery
SelectionGroup

CardinalityRequirement
CapabilityRequirement

FaultSpec
ResolvedFaultSpec

ControlAuthorityMode
ControlAuthoritySpec
ResolvedControlAuthoritySpec

HookSpec
CallableIdentity
```

Required deterministic identities include:

```text
problem_spec_sha256
resolved_problem_sha256
```

A04 schemas may reserve A05-facing fields/interfaces but may not define A05 temporal/profile shapes.

### `problem/resolution.py`

Performs one-time strict resolution:

```text
ProblemSpec
+ SemanticRegistryBundle
+ CircuitInventory
        ↓
ResolvedProblemSpec
```

Responsibilities include:

- exact semantic references;
- semantic queries;
- named/ordered groups;
- cardinality checks;
- deterministic ordering;
- duplicate/collision detection;
- capability requirements;
- fault-target resolution;
- authority conflict resolution;
- hook provenance resolution.

No AltDSS object rediscovery occurs here.

### `problem/spaces.py`

Compiles:

```text
ResolvedProblemSpec
        ↓
canonical Gymnasium spaces
```

and produces at least:

```text
observation_space
action_space
observation_layout
action_layout

observation_space_sha256
action_space_sha256
gym_space_contract_sha256
```

## 6. Frozen Complex-Quantity Representation

A03 contains complex-valued native electrical quantities.

A04 canonical Gym spaces use a lossless real-valued representation:

\[
z=a+jb \longrightarrow [a,b].
\]

Therefore:

```text
complex scalar
    -> float64 shape (2,)
       final axis = [real, imag]

complex vector shape (N,)
    -> float64 shape (N,2)

complex tensor shape (...)
    -> float64 shape (...,2)
```

The final axis has explicit semantic metadata:

```text
[real, imag]
```

OpenDSSSim does **not** convert canonical complex quantities to magnitude/angle because that would introduce a derived transform.

This representation is:

- deterministic;
- lossless;
- controller-neutral;
- compatible with A04.6.

## 7. Static Action-Space Compilation

Where A03 provides sufficient static metadata, A04 compiles canonical static outer domains.

Examples:

```text
PVSystem kvar
Storage kW / kvar
Transformer / AutoTrans taps
Capacitor states
Line open_close
```

A stricter ProblemSpec may narrow the static outer domain.

A04 does not add a second electrical-feasibility engine after this compilation.

State-dependent/native electrical feasibility remains AltDSS/OpenDSS responsibility as frozen in A04.5.

## 8. Runtime Semantic Access Layer

The existing A03 compiler remains unchanged.

A new `runtime/access.py` executes already-defined A03 addresses.

Conceptually:

```text
NativePropertyAddress
    -> backend property read/write

RuntimeReadoutAddress
    -> backend runtime-channel read

RuntimeCommandAddress
    -> backend runtime command
```

The backend abstraction is extended narrowly with operations conceptually equivalent to:

```python
write_object_property(...)

read_runtime_channel(...)

apply_runtime_command(...)
```

Existing property-read and solve behavior remains available.

## 9. AltDSS Backend Binding

`AltDSSBackend` implements only the qualified runtime vocabulary required by registered A03 addresses.

Initial runtime-readout qualification covers the currently registered A03 categories, including as applicable:

- bus voltage / pu voltage;
- circuit-element currents;
- terminal powers;
- losses;
- open state;
- transformer / autotransformer taps;
- solution convergence;
- topology/connectivity information.

Initial runtime-command qualification covers registered command semantics such as:

- transformer/autotransformer tap command;
- circuit-element open/close command.

Native-property writes cover registered actions and qualified `Enabled` behavior.

Exact AltDSS access syntax is established by genuine qualification, not assumed from documentation alone.

## 10. Runtime Schemas

`runtime/schema.py` contains conceptually:

```text
ProblemRuntimeBinding
RuntimeStepContext

ActionApplicationStatus
ActionChannelAudit
RuntimeStepRecord

HistoryLevel
ExecutionProfile

A04RuntimePreflightRecord
```

The action-status vocabulary remains narrow and does not create a duplicate electrical-feasibility engine.

## 11. Runtime Binding

`runtime/binding.py` binds:

```text
ResolvedProblemSpec
+ compiled Gym spaces
+ backend/runtime capability
        ↓
immutable ProblemRuntimeBinding
```

It resolves executable readers/writers, native/external authority, native-control suppression, static-fault `Enabled` handles, plant hooks, and runtime provenance.

It produces:

```text
runtime_binding_sha256
```

Binding occurs before the iterative run, not once per step.

## 12. Plant Adaptation

`plant/core.py` is extended rather than rewritten.

Existing behavior is preserved:

```text
reset / prepare
    -> load/compile
    -> solve
    -> inventory/semantic registry

solve_snapshot
    -> reuse loaded context
    -> solve
```

A04 builds on this with a one-time initialization/preparation boundary and then continued stepping on the same live AltDSS/OpenDSS context.

## 13. Environment Adaptation

`OpenDSSSimulator` gains optional problem/runtime configuration while preserving `problem=None`.

Conceptually:

```python
OpenDSSSimulator(
    network,
    problem=None,
    history_level=...,
    execution_profile=...,
    preflight_dir=...,
)
```

Static preparation includes:

```text
prepare feeder/A03 contract
resolve ProblemSpec
compile Gym spaces
build runtime binding
verify or reuse A04 preflight
```

Iterative `step()` performs only step-dependent work:

```text
canonical action validation
finite check
fault lockout
authority check
apply external command
solve live context
read semantic state
construct canonical observation
construct RuntimeStepContext
invoke hooks
record configured runtime history
return Gym step tuple
```

No per-step feeder recompile, semantic rediscovery, or problem resolution.

## 14. Recorder/History Foundation

A04 implements the foundational in-memory history surface required by the frozen architecture.

The established independent dimensions remain:

```text
history retention:
H0 / H1 / H2 / H3

execution instrumentation:
FAST / STANDARD / AUDIT
```

A04 does not create a competing recorder taxonomy.

Configured history may retain increasing amounts of:

- canonical observations;
- requested/applied/realized action data;
- internal semantic states;
- disturbances/parameters available at runtime;
- fault/availability state;
- authority state;
- solution/convergence/backend status;
- reward;
- termination;
- truncation;
- runtime identities;
- step index.

The purpose is to support later:

- metrics;
- analysis;
- debugging;
- visualization;
- reproducibility.

A05 later adds authoritative simulation-time identity and exogenous temporal information.

## 15. Persistent A04 Preflight

`persistence/preflight.py` follows the existing atomic persistence pattern.

A successful preflight record is keyed by all plant/problem/runtime dependencies that can invalidate compatibility, including:

- OpenDSSSim implementation identity;
- backend/runtime version;
- circuit/inventory identity;
- A03 registry identity;
- ProblemSpec identity;
- ResolvedProblemSpec identity;
- Gym-space identities;
- runtime-binding identity;
- hook identities;
- relevant schema versions.

When these remain identical, controller-internal algorithm changes may reuse the same A04 plant-preflight PASS.

Cached preflight does not eliminate the feeder compilation/solve required to run physics; it avoids re-proving unchanged static compatibility.

## 16. Four-Patch A04 Implementation Sequence

### A04I1 - Problem Contract + Resolution + Gym Spaces

Scope:

- add `problem/`;
- schemas and hashes;
- refs/queries/groups/cardinality;
- observation/action resolution;
- capability/fault/authority schema resolution;
- complex real/imag encoding;
- deterministic layout metadata;
- Gym-space compilation;
- `problem=None` compatibility.

No runtime command/writer implementation in A04I1.

### A04I2 - Semantic Runtime Access + AltDSS Binding

Scope:

- add `runtime/access.py`;
- adapt backend ABC;
- adapt `AltDSSBackend`;
- execute `NativePropertyAddress`, `RuntimeReadoutAddress`, `RuntimeCommandAddress`;
- qualify registered reads/writes/commands;
- qualify `Enabled=False`;
- preserve A03 source byte identity.

### A04I3 - Runtime Binding + Environment + History + Preflight

Scope:

- runtime schemas;
- runtime identity;
- immutable binding;
- one-time initialization;
- persistent live-context stepping;
- NATIVE / EXTERNAL / HYBRID ownership;
- static faults;
- requested/applied/realized audit;
- reward/termination/truncation hooks;
- H0-H3 foundational history;
- preflight persistence/reuse;
- environment/plant integration.

### A04I4 - Full Behavioral Qualification + Implementation Freeze

Scope:

- `validate_a04.py`;
- complete A01-A03 predecessor regression;
- genuine AltDSS A04 behavioral matrix;
- source-manifest freeze;
- final A04 implementation qualification report;
- persistent implementation-preflight authority.

## 17. Test Layout

Tests are additive.

Planned locations include:

```text
tests/unit/problem/
tests/unit/runtime/
tests/unit/persistence/test_a04_preflight.py

tests/integration/
    test_a04_problem_runtime.py
    test_a04_runtime_access.py
    test_a04_fault_authority.py
    test_a04_preflight_reuse.py
```

The existing A03 semantic fixture is reused first.

A new fixture is added only when a required A04 behavior cannot be exercised cleanly with existing qualified fixtures.

All predecessor tests remain passing after every A04 implementation patch.

## 18. Implementation Guardrails

A04 implementation must not:

- alter A03 semantics merely to simplify runtime access;
- implement controller-side observation feature engineering;
- implement generic observation/action wrappers;
- embed A05 profile/horizon tensor assumptions;
- duplicate OpenDSS electrical-feasibility logic;
- allow controller direct AltDSS mutation;
- silently clip/project/rescue controller actions;
- recompile/rebind/re-resolve every iteration;
- bypass predecessor regressions.

## 19. A05 Starts After A04 Implementation Freeze

Once A04I4 qualifies and A04 implementation is frozen, A05 becomes the next generalized-plant development stage.

A05 will ratify and implement:

- simulator clock;
- episode-time semantics;
- load profile shape and mapping;
- weather/outdoor-temperature shape and mapping;
- irradiance shape and mapping;
- PV availability/profile shape and mapping;
- exogenous replay/indexing;
- forecast horizon and forecast tensor shape;
- truth versus controller information;
- forecast error/uncertainty;
- time-varying faults/repairs/events;
- reproducibility and temporal qualification.

Thus exogenous load/temperature/irradiance/PV temporal shapes are intentionally **not** an A04 implementation dependency.

## 20. Ratification Decision

This A04 implementation plan is RATIFIED.

After this documentation patch is independently qualified, A04I1 source implementation is authorized within the scope frozen above.

A04I2-A04I4 remain sequentially gated by qualification of their predecessors.
