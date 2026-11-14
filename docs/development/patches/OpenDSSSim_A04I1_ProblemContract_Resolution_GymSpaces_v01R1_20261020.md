# Patch Record - OpenDSSSim_A04I1_ProblemContract_Resolution_GymSpaces_v01R1_20261020

**Date:** 2026-10-20  
**Stage:** A04I1 - Problem Contract + Resolution + Gym Spaces  
**Type:** Source implementation + unit qualification  
**Runtime writes:** NONE  
**Backend mutation:** NONE  
**Environment/plant lifecycle integration:** NONE

## Predecessor Authority

- Repository files: 155
- A04 implementation-plan qualified source-manifest SHA256: `994A923B67086F0B46EE91A9452FA4C46B3CDB2CF9F4AD53728738E1CDA76B33`

## Scope

A04I1 implements the controller-neutral problem-definition layer above frozen A03 semantics and below runtime binding.

### New problem package

```text
src/opendsssim/problem/
    __init__.py
    schema.py
    resolution.py
    spaces.py
```

Implemented contracts include:

- immutable `ProblemSpec` and `ResolvedProblemSpec`;
- deterministic `problem_spec_sha256` and `resolved_problem_sha256`;
- exact semantic references;
- semantic queries;
- named/ordered groups;
- `ANY`, `NONEMPTY`, `EXACT(n)`, `RANGE(min,max)` cardinality;
- current observation selection from A03 state/disturbance/parameter registries;
- action selection strictly from A03 `ActionRegistry`;
- capability requirements;
- fault-target resolution against the circuit inventory;
- NATIVE / EXTERNAL / HYBRID authority-contract resolution;
- deterministic static action outer bounds where A03 parameter semantics are sufficient;
- stricter problem-level restrictions that may narrow but not enlarge intrinsic bounds;
- canonical nested Gymnasium Dict-space compilation;
- deterministic layout metadata and space SHA256 identities;
- lossless complex-valued encoding using final-axis `[real, imag]` float64 representation;
- legacy `problem=None` Gym contract preservation.

## Explicit A05 Boundary

A04I1 does not define temporal/profile tensor shapes for load, outdoor temperature, irradiance, PV availability, forecasts, forecast uncertainty, or episode-time indexing.

A non-empty forecast observation request fails explicitly with `A05DeferredError` until A05 is ratified and implemented.

## Runtime Guard

A04I1 performs no OpenDSS/AltDSS writes and adds no runtime action execution.

The following existing runtime layers remain byte-identical to the predecessor:

- `src/opendsssim/backends/*`
- `src/opendsssim/plant/*`
- `src/opendsssim/environment/*`
- frozen A03 semantic compiler/schema/policy and persistence implementation.

A04I2 owns semantic runtime access and backend read/write/command binding.
A04I3 owns environment/plant runtime integration.

## Modified Files

1. `pyproject.toml` - package alpha version advanced to `0.1.0a4`.
2. `src/opendsssim/__init__.py` - additive A04I1 exports and `A04I1_PATCH_ID`; historical A03 `PATCH_ID` is preserved for predecessor validation compatibility.

## Added Tests

A04I1 adds unit coverage for:

- deterministic problem hashes;
- exact/query/group selection;
- deterministic query ordering;
- query/group cardinality;
- duplicate-channel failure;
- capability failure;
- A05 forecast deferral;
- authority contracts;
- problem-bound narrowing versus enlargement;
- PV/storage/tap action bounds;
- categorical switch domain;
- complex real/imag encoding;
- semantic space layouts/hashes;
- `problem=None` compatibility.

## Qualification Gate

A04I1 is accepted only if:

- exact predecessor identity is verified;
- all non-allowlisted predecessor files remain byte-identical;
- frozen A03 source remains byte-identical;
- Python compile passes;
- targeted A04I1 unit tests pass;
- complete repository pytest regression passes;
- repository/source manifest is emitted for the qualified A04I1 state.

## Next

After independent A04I1 qualification:

**A04I2 - Semantic Runtime Access + AltDSS Binding** becomes eligible.
