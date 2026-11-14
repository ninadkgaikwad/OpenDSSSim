# A03.6 — Runtime Compilation and Reuse

## 1. First valid compile

A03 may perform a one-time semantic compilation using:

```text
validated CircuitInventory
        +
frozen A03 semantic policy
        +
one-time read-only static metadata extraction
        |
        v
canonical semantic entries
        |
        v
seven registry views
        |
        v
SemanticRegistryBundle
```

## 2. A03 must not rerun A02 discovery

When A02H1 inventory is valid, A03 must not call full A02 circuit discovery merely to
classify semantics.

The A02H1 inventory already defines physical existence and structure.

## 3. One-time static metadata extraction

A02H1 intentionally does not persist every property value because many values may be
dynamic or unsuitable as persistent truth.

A03 is therefore allowed to read **specific static metadata once** when that metadata is
required for semantic definitions.

Examples can include:

- ratings;
- tap bounds;
- discrete device domains;
- native-controller configuration metadata;
- fixed electrical/model configuration required by parameter/constraint semantics.

The read set must be explicit and policy-driven rather than a second "dump everything"
discovery pass.

## 4. Episode lifecycle

Once a valid bundle exists:

```text
env.reset()
   -> load/recompile physical circuit as required by plant lifecycle
   -> validate/reuse A02H1 CircuitInventory
   -> validate/reuse A03 SemanticRegistryBundle
   -> no semantic reclassification
```

Repeated episodes must not rebuild semantic registries solely because a reset occurred.

## 5. New process/environment instance

A new simulator instance may reuse a persisted registry bundle if all source inventory,
schema, semantic-policy, backend, and engine identity checks pass.

## 6. Explicit semantic recompilation

Semantic recompilation occurs when:

- no bundle exists;
- A02H1 inventory/source identity changes;
- A03 schema changes;
- semantic policy changes;
- backend/engine compatibility identity invalidates the bundle.

## 7. Live runtime readouts

A persistent `RuntimeReadoutAddress` defines **how to obtain** a current value.

It does not contain the current value.

At runtime, state/observation services read the live backend using the address and
selectors defined by A03.

## 8. Live commands

A persistent `NativePropertyAddress` or `RuntimeCommandAddress` in `ActionRegistry`
defines a legitimate possible plant command.

A03 does not apply the command.

Later action validation/authority/runtime stages execute requested commands through the
plant-owned `env.step(...)` path.

## 9. Controller independence

Registry compilation is controller-independent.

RBC, MPC, and RL later consume the same plant semantic catalog rather than constructing
their own private mappings into AltDSS.
