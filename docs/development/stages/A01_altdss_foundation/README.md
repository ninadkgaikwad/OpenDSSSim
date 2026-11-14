# A01 — AltDSS Foundation / Context / Snapshot

**Status:** FINAL/FROZEN  
**Qualified patch:** `OpenDSSSim_A01_AltDSS_Foundation_Context_Snapshot_v01R1_20261005`

## Responsibility

A01 establishes the minimum authoritative simulator plant foundation:

- one independent AltDSS context per simulator/backend instance;
- DSS source validation and circuit loading;
- deterministic snapshot solve;
- reset/recompile on the same owned context;
- typed solution status;
- close lifecycle;
- minimal Gymnasium wrapper.

A01 deliberately does not generalize control/state semantics. Its Gym action surface is
empty and its initial observation surface is minimal.

## Why the boundary exists

Later controller, registry, and time-series work must build on a proven plant lifecycle
without gaining direct ownership of AltDSS state.

## Inputs

- DSS master source;
- AltDSS-Python environment;
- backend selection.

## Outputs

- owned backend/context;
- loaded circuit identity;
- snapshot solution result;
- minimal Gym reset/step lifecycle;
- runtime provenance/manifest support.

## Invariants

1. different simulator instances do not share the same AltDSS context;
2. all physical solves occur through the owned backend/plant;
3. reset reuses the simulator-owned context rather than sharing global state;
4. close is explicit and idempotent;
5. no controller logic is embedded in the backend.

## Deferred

A01 does not implement:

- generalized circuit discovery;
- persistent circuit inventory;
- semantic registries;
- generalized actions/observations;
- external time progression;
- controllers.

## Authoritative records

- patch: `docs/development/patches/OpenDSSSim_A01_AltDSS_Foundation_Context_Snapshot_v01R1_20261005.md`
- environment: `docs/development/environment/README.md`
- successor discovery contract: `docs/development/architecture/OpenDSSSim_A02_Generalized_Engine_Circuit_Capability_Discovery_Contract_v01_20261006.md`
