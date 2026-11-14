# A03.5 — Persistence, Cache Identity, and Invalidation

## 1. Persistent artifact

A03 persists one atomic machine-readable artifact:

```text
SemanticRegistryBundle.json
```

Seven registries are serialized inside one bundle so their identities, semantic policy,
and source inventory cannot drift independently.

## 2. Required bundle identity

The persisted bundle must carry at least:

```text
registry_schema_version
semantic_policy_version
semantic_policy_sha256

source_inventory:
    inventory_semantic_sha256
    source_tree_sha256
    backend
    altdss_version
    engine_version

semantic_entries
CircuitRegistry
StateRegistry
ActionRegistry
DisturbanceRegistry
ConstraintRegistry
ParameterRegistry
CapabilityRegistry

bundle_semantic_sha256
```

Exact Python field names may differ if the implementation contract preserves the same
meaning.

## 3. Semantic policy identity

The class-by-class policy is part of scientific/software provenance.

If policy changes, for example:

```text
some quantity:
INIT_ONLY -> STEP_CONTROLLABLE
```

the semantic-policy version/hash must change even when the DSS files do not.

A registry compiled under the prior policy is then invalid.

## 4. Invalidation inputs

Registry reuse must depend on at least:

1. A02H1 inventory semantic SHA256;
2. A02H1 source-tree SHA256;
3. A03 registry schema version;
4. A03 semantic-policy version;
5. A03 semantic-policy SHA256;
6. backend identity;
7. compatible AltDSS/DSS engine identity.

## 5. Why both inventory and source-tree identities are retained

The A02H1 inventory semantic hash proves static discovered structure.

The source-tree fingerprint proves authoritative circuit-source provenance.

Retaining both makes invalidation conservative and auditable.

## 6. Cache behavior

Conceptual lifecycle:

```text
valid CircuitInventory
        |
        v
compute A03 semantic cache identity
        |
        v
SemanticRegistryBundle exists and validates?
       / \
     yes  no
      |    |
    load   compile once
      |      |
      |    persist atomically
      |      |
      +------+
        |
        v
runtime uses semantic bundle
```

## 7. Atomicity

A partially written semantic bundle must never be treated as valid.

The implementation should use the same safe persistence principle established by A02H1:
write a complete temporary artifact, validate/close it, then atomically replace the target.

## 8. Default cache location

The final implementation should keep generated semantic artifacts outside authoritative DSS
source directories and outside repository source by default, while allowing an explicit
reproducibility/output directory.

The exact cache directory is frozen in the A03 implementation contract.

## 9. Static-only persistence

The semantic bundle contains definitions and static metadata.

It must not persist the current episode's:

- voltage;
- current;
- power;
- tap position;
- capacitor realization;
- switch realization;
- SOC;
- convergence;
- realized native-controller behavior;
- requested/applied/realized external action.

Those values are runtime data.
