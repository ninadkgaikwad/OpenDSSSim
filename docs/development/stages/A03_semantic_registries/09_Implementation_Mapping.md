# A03.9 — Implementation Mapping

**Implementation patch:** `OpenDSSSim_A03_Persistent_Seven_Semantic_Registries_v01R4_20261010`  
**Normative semantic-policy SHA256:** `51062A587FF88E8B33A1CA2F6BA57B182D58AF8A83A16EE8D0CA0F7D072A98E3`

This file is an implementation map, not a new semantic-policy authority. The normative A03 documents remain the ten-file A03D1 policy set.

## Source mapping

- `src/opendsssim/semantics/schema.py`
  - three semantic address families;
  - four mutability classes;
  - canonical `SemanticEntry`;
  - typed seven-registry schemas;
  - deterministic semantic IDs and bundle hash.
- `src/opendsssim/semantics/policy.py`
  - compiled identity of the frozen A03D1 semantic policy;
  - explicit class/property metadata and constraint mappings;
  - native-control capability mappings.
- `src/opendsssim/semantics/compiler.py`
  - `CircuitInventory -> SemanticRegistryBundle` compiler;
  - explicit class-by-class semantic classification;
  - conservative action promotion;
  - capability derivation.
- `src/opendsssim/persistence/semantic_registry.py`
  - deterministic cache identity;
  - atomic JSON persistence;
  - schema/policy/inventory/source/backend/engine validation;
  - corrupted bundle rejection.
- `src/opendsssim/backends/base.py` and `altdss_backend.py`
  - explicit read-only property-subset API used only for policy-selected static metadata;
  - no broad A02 rediscovery.
- `src/opendsssim/plant/core.py`
  - A02H1 inventory reuse followed by A03 semantic bundle reuse/compile;
  - one compilation per valid identity;
  - cache invalidation and rebuild.
- `src/opendsssim/environment/simulator.py`
  - exposes semantic bundle/status/provenance;
  - preserves A03 empty action space and minimal observation space pending A04.

## Cache rule

If an explicit `semantic_registry_dir` is supplied, A03 uses it. If only `inventory_dir` is supplied, A03 uses `<inventory_dir>/semantic_registry`. Otherwise the platform default is `%LOCALAPPDATA%/OpenDSSSim/semantic_registry` on Windows or `~/.opendssim/semantic_registry` fallback.

## Conservative A03-v1 decisions

- Generator `kW/kvar` are not promoted to external `STEP_CONTROLLABLE` actions in v1.
- Native controller configuration remains `INIT_ONLY` parameter semantics.
- `RegControl` settings do not replace the physical transformer tap command endpoint.
- `CapControl` settings do not replace the physical capacitor state endpoint.
- `SwtControl` settings do not replace the physical branch open/close endpoint.
- Line configuration such as `R1` remains outside `ActionRegistry` even if writable in AltDSS.
- P1 operating voltage bounds remain outside A03.

## Qualification mapping

`validate_a03.py` and A03-specific tests verify:

- all three address families;
- all four mutability classes;
- seven registries;
- real Load/PV/Storage/Capacitor/Transformer/Line/Generator classification;
- native-controller versus physical-endpoint separation;
- runtime readout and runtime command addresses;
- source/schema/policy/corruption invalidation;
- same-process and new-process cache reuse;
- no A02 rediscovery and no A03 static reclassification when caches are valid;
- unchanged A01/A02/A02H1 behavior.
