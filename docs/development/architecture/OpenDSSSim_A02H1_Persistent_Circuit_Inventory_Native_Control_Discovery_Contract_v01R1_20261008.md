# OpenDSSSim A02H1 Persistent Circuit Inventory + Native OpenDSS Control Discovery Contract

## 1. Identity

- Contract ID: `OpenDSSSim_A02H1_Persistent_Circuit_Inventory_Native_Control_Discovery_Contract_v01R1_20261008`
- Patch ID: `OpenDSSSim_A02H1_Persistent_Circuit_Inventory_Native_Control_Discovery_v01R1_20261008`
- Date: 2026-10-08
- Status: **FROZEN for A02H1 implementation**
- Predecessor: `OpenDSSSim_A02_Generalized_Engine_Circuit_Capability_Discovery_v01R1_20261007`
- Predecessor source-manifest SHA256: `391A3AEC79882BFE2BCA7DF7DAFA2399AF42EE9A10A9FDD478727B5B84859983`
- Environment: `scalebridge-dev-gpu-laptop`
- AltDSS: `0.2.4`


## Rebase authority

A02H1 v01 was never installed: its installer correctly rejected a stale
70-file predecessor after the parallel controller-science track advanced.

This v01R1 revision preserves the A02H1 implementation semantics and rebases
only its repository authority onto the audited 72-file shared state:

- original frozen A02 files: 70;
- controller-science files modified since A02 freeze: 10;
- controller-science files added since A02 freeze: 2;
- missing files: 0;
- plant/source/test/A02 architecture drift: NONE;
- rebased predecessor source-manifest SHA256:
  `391A3AEC79882BFE2BCA7DF7DAFA2399AF42EE9A10A9FDD478727B5B84859983`.

No A02H1 payload path is permitted under `docs/development/control_science/`.

## 2. Architectural objective

A02H1 hardens the frozen A02 read-only discovery layer in two ways:

1. native OpenDSS control/protection objects are explicitly recognized and their
   relationships to controlled/monitored/switched/protected objects are recorded;
2. static circuit discovery is compiled once into a deterministic machine-readable
   `CircuitInventory` and reused across episodes/environments while its identity remains valid.

A02H1 remains descriptive. It does **not** make a native control property an
OpenDSSSim external action.

## 3. Official native control-element catalog

A02H1 uses the DSS-Extensions/OpenDSS control-element catalog:

```text
CapControl
ESPVLControl
ExpControl
Fuse
GenDispatcher
InvControl
Recloser
RegControl
Relay
StorageController
SwtControl
UPFCControl
```

`GICTransformer` is a power-delivery element, not a control object, and is not
classified as a native controller.

The implementation remains class-driven and circuit-general. Only instantiated
objects are added to a circuit's inventory.

## 4. Native relationship roles

Machine-readable relationships use native OpenDSS full names and explicit roles:

```text
CONTROLS
MONITORS
MONITORS_BUS
SWITCHES
PROTECTS
COORDINATES_CONTROL
```

Examples include:

- `RegControl -> Transformer/AutoTrans`;
- `CapControl -> monitored Element` and `Capacitor`;
- `InvControl -> DERList`, with the documented all-PVSystem/Storage default;
- `GenDispatcher -> monitored Element` and `GenList`, with all-generator default;
- `StorageController -> monitored Element` and `ElementList`;
- `SwtControl -> SwitchedObj`;
- `Relay/Recloser/Fuse -> MonitoredObj` and protected `SwitchedObj`;
- `ExpControl -> PVSystemList/DERList`;
- `UPFCControl -> UPFCList`;
- `ESPVLControl -> monitored Element and explicit coordinated resource/control lists`.

Default relationships are labeled as defaults rather than disguised as explicit
user declarations.

## 5. Source dependency identity

A01/A02 retained the master-file SHA256 for compatibility.

A02H1 adds a conservative **source-tree SHA256**. By default, every regular file
under the master file's parent directory participates in the dependency manifest.

Excluded generated/cache/VCS trees are only:

```text
.git
.opendsssim
.pytest_cache
__pycache__
*.pyc
```

A caller may provide a broader `source_root` when authoritative dependencies live
above the master directory.

This policy deliberately favors safe over-invalidation over stale inventory reuse.

## 6. CircuitInventory contents

The persisted inventory contains only static compiler/circuit facts:

- inventory/relationship/discovery schema versions;
- backend, AltDSS, and engine versions;
- master relative path and master SHA256;
- source-tree SHA256;
- full source-dependency manifest;
- circuit name and static shape counts;
- A02 discovery semantic SHA256 as build provenance;
- buses and node names;
- instantiated DSS classes;
- object identities and property-name metadata;
- circuit-element phase/terminal/conductor/node/bus structure;
- static existence of attached switch/voltage/OCP control;
- native control-object catalog/presence;
- native control relationships.

## 7. Explicitly excluded dynamic runtime truth

The persistent inventory does **not** contain:

```text
solution_converged
object properties_json values
element is_isolated state
context_identity
live voltages
live currents/powers
live tap positions
live capacitor states
live switch states
storage SOC
control queue state
realized control actions
```

Those remain runtime state.

## 8. Cache identity and location

Inventory cache identity includes:

- inventory schema version;
- relationship schema version;
- A02 discovery schema version;
- backend;
- AltDSS version;
- DSS engine version;
- master relative path;
- source-tree SHA256.

The default inventory directory is machine-local and outside circuit/repository
source trees:

- Windows: `%LOCALAPPDATA%/OpenDSSSim/inventory`
- fallback: `~/.opendsssim/inventory`

Callers may supply `inventory_dir` to place reproducibility artifacts in a shared
paper/data location.

## 9. Runtime lifecycle

First use or invalidated source:

```text
CircuitSource fingerprint
    -> load/solve circuit
    -> A02 live discovery once
    -> native control relationship derivation
    -> build CircuitInventory
    -> atomic JSON write
```

Later episodes in the same environment:

```text
reset()
    -> reload/solve circuit
    -> reuse in-memory inventory
    -> NO static rediscovery
```

Later environments/processes:

```text
CircuitSource fingerprint
    -> exact inventory cache key
    -> load + validate JSON
    -> load/solve circuit
    -> reuse persisted inventory
    -> NO static rediscovery
```

Any source/schema/backend/engine mismatch creates a cache miss and rebuilds.

## 10. A02 preservation

A02 remains the raw live-discovery service. Explicit calls to
`discover_circuit()` still perform live A02 discovery.

A02H1 only guarantees that ordinary runtime reset/step does not repeat that
discovery after a valid inventory exists.

## 11. REUSE / ADAPT / NEW / DEFER

### REUSE

- independent AltDSS context ownership;
- A01 load/reset/snapshot solve;
- A02 native object/class/bus/element discovery;
- A02 full property snapshot as one-time compiler input;
- Gymnasium plant boundary;
- native OpenDSS vocabulary.

### ADAPT

- `CircuitSource`: add source-root dependency manifest/tree SHA256;
- plant: load/build/reuse static inventory;
- simulator: expose inventory status/path/hash without changing physics/spaces;
- A02 validator: use frozen A02 predecessor patch identity under successors;
- persistence package: add inventory schemas and atomic JSON I/O.

### NEW

- native control catalog;
- control/protection relationship extraction;
- persistent `CircuitInventory`;
- inventory semantic SHA256;
- cache key/invalidation logic;
- source-tree dependency fingerprint;
- A02H1 validator and fixtures/tests.

### DEFER TO A03+

- seven semantic registries;
- mutability classification;
- native-vs-external control authority;
- controller compatibility/UNSUPPORTED outcome;
- ProblemSpec;
- generalized observation/action spaces;
- dynamic topology/state services;
- time-series progression;
- MPC/RL/controller implementation.

## 12. Qualification gates

A02H1 must prove:

1. exact 72-file rebased predecessor identity, including preservation of all audited controller-science changes;
2. source-tree fingerprint includes nested dependent files;
3. changing a non-master dependency invalidates identity;
4. official native control catalog is frozen;
5. real AltDSS control objects are discovered in a fixture;
6. real controller->target relationships are resolved;
7. inventory is built and atomically persisted on first use;
8. same-environment resets do not rediscover;
9. a new environment reuses a valid persisted inventory without rediscovery;
10. source change produces a cache miss;
11. persisted inventory omits dynamic runtime fields;
12. A01 regression remains PASS;
13. A02 regression remains PASS;
14. full repository pytest remains PASS;
15. environment remains unchanged.

## 13. Successor

A03 consumes the validated `CircuitInventory` and builds/persists the seven
semantic registries once per valid circuit configuration.
