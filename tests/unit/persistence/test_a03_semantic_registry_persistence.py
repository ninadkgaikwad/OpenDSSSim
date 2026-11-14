from dataclasses import replace
from pathlib import Path

from opendsssim.persistence.inventory_schema import CircuitInventory
from opendsssim.persistence.semantic_registry import (
    load_valid_semantic_registry,
    semantic_registry_cache_key,
    semantic_registry_path_for_inventory,
    validate_bundle_for_inventory,
    write_semantic_registry_bundle,
)
from opendsssim.semantics.policy import SEMANTIC_POLICY_SHA256
from opendsssim.semantics.schema import (
    ActionRegistry,
    CapabilityRegistry,
    CircuitRegistry,
    ConstraintRegistry,
    DisturbanceRegistry,
    ParameterRegistry,
    SEMANTIC_POLICY_VERSION,
    SEMANTIC_REGISTRY_SCHEMA_VERSION,
    SemanticRegistryBundle,
    StateRegistry,
)


def _inventory(source_tree: str = "A" * 64) -> CircuitInventory:
    return CircuitInventory(
        schema_version="A02H1.inventory.v1",
        relationship_schema_version="A02H1.control-relations.v1",
        discovery_schema_version="A02.v1",
        backend="altdss",
        altdss_version="0.2.4",
        engine_version="engine",
        master_relative_path="Master.dss",
        master_sha256="B" * 64,
        source_tree_sha256=source_tree,
        source_dependencies=(),
        circuit_name="test",
        num_buses=0,
        num_nodes=0,
        num_circuit_elements=0,
        a02_discovery_semantic_sha256="C" * 64,
        buses=(),
        node_names=(),
        classes=(),
        objects=(),
        elements=(),
        native_control_catalog=(),
        native_controls=(),
        control_relationships=(),
    )


def _bundle(inventory: CircuitInventory) -> SemanticRegistryBundle:
    return SemanticRegistryBundle(
        registry_schema_version=SEMANTIC_REGISTRY_SCHEMA_VERSION,
        semantic_policy_version=SEMANTIC_POLICY_VERSION,
        semantic_policy_sha256=SEMANTIC_POLICY_SHA256,
        source_inventory_semantic_sha256=inventory.semantic_sha256,
        source_tree_sha256=inventory.source_tree_sha256,
        backend=inventory.backend,
        altdss_version=inventory.altdss_version,
        engine_version=inventory.engine_version,
        semantic_entries=(),
        circuit_registry=CircuitRegistry("test", (), (), (), (), ()),
        state_registry=StateRegistry(()),
        action_registry=ActionRegistry(()),
        disturbance_registry=DisturbanceRegistry(()),
        constraint_registry=ConstraintRegistry(()),
        parameter_registry=ParameterRegistry(()),
        capability_registry=CapabilityRegistry(()),
    )


def test_cache_key_changes_with_source_or_policy_identity():
    a = _inventory("A" * 64)
    b = _inventory("D" * 64)
    assert semantic_registry_cache_key(a) != semantic_registry_cache_key(b)
    assert semantic_registry_cache_key(a) != semantic_registry_cache_key(
        a,
        semantic_policy_sha256="E" * 64,
    )


def test_schema_and_policy_mismatch_invalidate_bundle():
    inv = _inventory()
    bundle = _bundle(inv)
    assert validate_bundle_for_inventory(bundle, inv)[0]
    assert not validate_bundle_for_inventory(
        replace(bundle, registry_schema_version="future"), inv
    )[0]
    assert not validate_bundle_for_inventory(
        replace(bundle, semantic_policy_sha256="F" * 64), inv
    )[0]


def test_corrupt_bundle_is_rejected_without_crashing(tmp_path: Path):
    inv = _inventory()
    path = semantic_registry_path_for_inventory(
        inv,
        semantic_registry_dir=tmp_path,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not-json", encoding="utf-8")
    bundle, returned_path, reasons = load_valid_semantic_registry(
        inv,
        semantic_registry_dir=tmp_path,
    )
    assert bundle is None
    assert returned_path == path
    assert any("invalid" in reason for reason in reasons)


def test_atomic_write_round_trip(tmp_path: Path):
    inv = _inventory()
    bundle = _bundle(inv)
    path = semantic_registry_path_for_inventory(
        inv,
        semantic_registry_dir=tmp_path,
    )
    write_semantic_registry_bundle(path, bundle)
    loaded, _, reasons = load_valid_semantic_registry(
        inv,
        semantic_registry_dir=tmp_path,
    )
    assert reasons == ()
    assert loaded == bundle
