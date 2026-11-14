# A03 — Persistent Seven Semantic Registries

**Status:** DOCUMENTATION FROZEN / IMPLEMENTATION NOT YET AUTHORIZED  
**Documentation stage:** A03D1  
**Date:** 2026-10-09

## Purpose

A03 consumes a validated A02H1 `CircuitInventory` and compiles a persistent,
machine-readable semantic description of what the available circuit entities, properties,
readouts, commands, limits, and capabilities **mean to OpenDSSSim**.

```text
A02H1 CircuitInventory
        |
        v
A03 semantic compiler
        |
        v
SemanticRegistryBundle
        |
        +-- CircuitRegistry
        +-- StateRegistry
        +-- ActionRegistry
        +-- DisturbanceRegistry
        +-- ConstraintRegistry
        +-- ParameterRegistry
        +-- CapabilityRegistry
```

## Fundamental boundary

```text
A02H1: What physically exists?
A03:   What does it mean to OpenDSSSim?
A04:   What does this particular ProblemSpec expose/use?
```

A03 is generalized infrastructure. It does not know the paper-specific object identities
of the modified IEEE-123 feeder and does not hard-code P1's 30 selected control channels
or any future P2 switch set.

## Frozen architectural decisions

- three semantic address families:
  `NativePropertyAddress`, `RuntimeReadoutAddress`, `RuntimeCommandAddress`;
- four mutability classes:
  `READ_ONLY`, `INIT_ONLY`, `STEP_CONTROLLABLE`, `STEP_EXOGENOUS`;
- one persisted atomic `SemanticRegistryBundle`;
- seven registry views over canonical semantic definitions;
- A03 may perform one-time read-only static metadata extraction;
- A03 must not rerun A02 full physical discovery when A02H1 inventory is valid;
- writable AltDSS property != external action;
- `StateRegistry` != controller observation space;
- `ActionRegistry` != every problem's action space;
- native controller capability != external control authority;
- intrinsic plant constraint != paper/problem operating requirement;
- live runtime values are never registry truth.

## Documentation set

1. `01_Scope_and_Boundaries.md`
2. `02_Semantic_Address_and_Mutability_Model.md`
3. `03_Seven_Registry_Contracts.md`
4. `04_Class_by_Class_Semantic_Policy.md`
5. `05_Persistence_Cache_Identity_and_Invalidation.md`
6. `06_Runtime_Compilation_and_Reuse.md`
7. `07_Capability_and_Controller_Compatibility.md`
8. `08_Qualification_Plan_and_Evidence.md`

## Implementation authorization

Source implementation begins only after A03D1 documentation independently qualifies.
The implementation must conform to these files or explicitly revise the documentation
through a new versioned documentation patch.
