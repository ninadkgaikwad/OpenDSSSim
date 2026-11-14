# OpenDSSSim A02 Generalized Engine and Circuit Capability Discovery Contract

## 1. Identity

- Contract ID: `OpenDSSSim_A02_Generalized_Engine_Circuit_Capability_Discovery_Contract_v01_20261006`
- Patch ID: `OpenDSSSim_A02_Generalized_Engine_Circuit_Capability_Discovery_v01R1_20261007`
- Date: 2026-10-06
- Status: **FROZEN for A02 implementation**
- PRE-A02 source-manifest SHA256: `8D6A5D3548B90A515C38710B66ED6D814EE28E27C47E9D97FEAA680B7EE966A8`
- Environment: `scalebridge-dev-gpu-laptop`
- Installed AltDSS: `0.2.4`

## 2. Objective

A02 creates a deterministic, typed, read-only discovery snapshot of the owned
AltDSS engine and a loaded OpenDSS circuit.

A02 discovers facts. It does **not** assign controller semantics.

In particular:

> A property being exposed or editable by AltDSS does not make it an OpenDSSSim
> action.

A03 alone will classify discovered information into the seven generalized
registries and mutability classes such as `READ_ONLY`, `INIT_ONLY`, and
`STEP_CONTROLLABLE`.

## 3. Consumer requirements

The controller-science track currently requires, among other services:

- capability query (`CSI-001`);
- native circuit/object binding (`CSI-002`);
- explicit unsupported semantics later (`CSI-006`);
- non-mutating topology/model information (`CSI-008`).

A02 supplies the raw generalized discovery substrate for these later contracts.
It does not implement controller compatibility itself.

## 4. Canonical vocabulary

Native OpenDSS identities remain canonical.

Objects are identified using full native names:

```text
Class.Object
```

Examples:

```text
Load.Load1
Line.Feeder
PVSystem.PV1
Storage.BESS1
RegControl.Reg1
SwtControl.SW1
```

A02 does not replace these with a custom device ontology.

## 5. Engine discovery

`EngineDiscovery` records:

- discovery schema version;
- backend identifier;
- AltDSS package version;
- DSS engine version;
- process-local owned context identity;
- public AltDSS context surface;
- verified generalized feature flags.

A02 feature flags describe discovery infrastructure only. They are not
controller capabilities.

## 6. Circuit discovery

`CircuitDiscovery` records:

- circuit source SHA256;
- circuit name;
- bus/node/circuit-element counts;
- current solution-convergence flag;
- engine discovery;
- bus inventory;
- node names;
- instantiated DSS classes;
- instantiated native DSS objects;
- circuit-element structural metadata;
- topology summary.

The snapshot is JSON serializable.

## 7. Native object discovery

A02 discovers instantiated typed DSS object managers exposed by the installed
AltDSS context.

Generic heterogeneous batches (`Element`, `PCElement`, `PDElement`) are not
counted as additional object classes; they are used as structural views.

For each native object A02 stores:

- `full_name`;
- `dss_class`;
- `name`;
- whether it is a circuit element;
- full discovered property names;
- a canonical full-property JSON snapshot.

The full-property snapshot uses DSS-Extensions JSON export with `Full`,
`FullNames`, and explicit DSS-class inclusion.

Classes with no instantiated objects are absent from the circuit snapshot.

## 8. Circuit-element discovery

For each circuit element A02 records:

- canonical full name;
- native class/name;
- number of phases;
- number of terminals;
- conductors per terminal;
- node order, when available;
- node references, when available;
- native terminal bus specifications extracted from DSS property data;
- attached switch-control indicator;
- attached voltage-control indicator;
- attached overcurrent-protection indicator;
- current isolated indicator.

Terminal bus specifications are preserved as native DSS strings. A02 does not
reinterpret them as controller actions or a replacement topology model.

## 9. Bus and node discovery

A02 records:

- sorted native bus names;
- engine-order node names;
- per-bus node-name grouping where resolvable from native node names.

Bus names and node names retain OpenDSS spelling.

## 10. Topology summary

A02 exposes read-only topology facts directly supported by the AltDSS Topology
interface:

- isolated branches;
- isolated loads;
- looped pairs;
- isolated-branch count;
- isolated-load count;
- loop count.

A complete controller-facing graph/model service is **not** frozen in A02.
`CSI-008` remains a later synchronization item.

## 11. Determinism

For an unchanged circuit and engine state:

- repeated discovery in the same context must produce identical snapshots;
- independent contexts loaded with the same circuit must produce the same
  context-independent semantic fingerprint;
- process-local context identity must remain distinct across environments.

`CircuitDiscovery.semantic_sha256` excludes only `context_identity`.

## 12. Read-only contract

A02 discovery may navigate AltDSS selectors/collections internally but must not:

- issue circuit-edit commands;
- change DSS object properties;
- open/close circuit elements;
- change controller authority;
- advance the episode clock;
- alter the authoritative solution result;
- apply a controller action.

After discovery, the existing snapshot solve must remain valid and repeatable.

## 13. Error semantics

Engine discovery is valid before a circuit is loaded.

Circuit discovery before circuit load raises the existing typed
`CircuitNotLoadedError`.

Discovery failures are explicit; A02 does not silently fabricate missing
physical data.

`NodeOrder`/`NodeRef` are retained when available from the installed engine.
If the engine cannot provide them for an element, A02 records empty tuples and
does not infer replacements.

## 14. REUSE / ADAPT / NEW / DEFER ledger

### REUSE

- one independent AltDSS context per environment/backend;
- `CircuitSource`;
- deterministic circuit load/reset;
- snapshot solve;
- `SolutionResult`;
- Gymnasium `reset()`/`step()` plant lifecycle;
- existing source/provenance machinery.

### ADAPT

- `DistributionBackend`: add read-only engine/circuit discovery contracts;
- `AltDSSBackend`: implement discovery on its owned context;
- `OpenDSSPlant`: expose backend discovery;
- `OpenDSSSimulator`: expose read-only discovery without changing A01 spaces.

### NEW

- immutable discovery dataclasses;
- native DSS object/class enumeration;
- full-property metadata snapshots;
- circuit-element structural discovery;
- bus/node discovery;
- topology summary;
- context-independent semantic fingerprint;
- A02 standalone validator;
- A02 deterministic/isolation/read-only tests.

### DEFER TO A03+

- `CapabilityRegistry`;
- `CircuitRegistry`;
- `StateRegistry`;
- `ActionRegistry`;
- `DisturbanceRegistry`;
- `ConstraintRegistry`;
- `ParameterRegistry`;
- mutability classification;
- writable-property/action classification;
- unsupported-controller resolution;
- `ProblemSpec`;
- generalized Gym spaces;
- external time-series execution;
- controller implementation.

## 15. Qualification gates

A02 must prove:

1. PRE-A02 predecessor identity;
2. package/patch identity;
3. engine discovery before circuit load;
4. circuit discovery requires load;
5. independent context identity;
6. native bus/node inventory;
7. native object/class discovery;
8. native circuit-element structural metadata;
9. full property snapshot;
10. deterministic repeat discovery;
11. cross-context semantic parity;
12. JSON serialization;
13. read-only solution behavior;
14. successful post-discovery snapshot solve;
15. all A01 regressions remain PASS;
16. full repository pytest remains PASS;
17. no environment mutation.

## 16. Successor

A03 consumes these discovery snapshots to build the seven generalized registries
and to classify semantics. A02 itself remains purely descriptive.
