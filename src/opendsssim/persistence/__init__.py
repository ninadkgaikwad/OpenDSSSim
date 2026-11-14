"""Persistence contracts with lazy imports for circular-import safety."""

from .inventory_schema import (
    CONTROL_RELATIONSHIP_SCHEMA_VERSION,
    INVENTORY_SCHEMA_VERSION,
    CircuitInventory,
    NativeControlObject,
    NativeControlRelationship,
)
from .schema import RuntimeManifest

__all__ = [
    "CONTROL_RELATIONSHIP_SCHEMA_VERSION",
    "INVENTORY_SCHEMA_VERSION",
    "CircuitInventory",
    "NativeControlObject",
    "NativeControlRelationship",
    "RuntimeManifest",
    "build_circuit_inventory",
    "compute_source_identity",
    "default_inventory_dir",
    "inventory_path_for_source",
    "load_valid_inventory",
    "read_circuit_inventory",
    "validate_inventory_for_source",
    "write_circuit_inventory",
    "default_semantic_registry_dir",
    "load_valid_semantic_registry",
    "read_semantic_registry_bundle",
    "semantic_registry_cache_key",
    "semantic_registry_path_for_inventory",
    "validate_bundle_for_inventory",
    "write_semantic_registry_bundle",
    "write_runtime_manifest",
    "A04RuntimePreflightRecord",
    "PREFLIGHT_SCHEMA_VERSION",
    "default_preflight_dir",
    "ensure_preflight",
    "make_preflight_record",
    "preflight_path",
    "write_preflight",
]


def __getattr__(name: str):
    if name in {
        "compute_source_identity",
        "write_runtime_manifest",
    }:
        from . import manifest as module
        return getattr(module, name)

    if name in {
        "build_circuit_inventory",
        "default_inventory_dir",
        "inventory_path_for_source",
        "load_valid_inventory",
        "read_circuit_inventory",
        "validate_inventory_for_source",
        "write_circuit_inventory",
    }:
        from . import inventory as module
        return getattr(module, name)

    if name in {
        "default_semantic_registry_dir",
        "load_valid_semantic_registry",
        "read_semantic_registry_bundle",
        "semantic_registry_cache_key",
        "semantic_registry_path_for_inventory",
        "validate_bundle_for_inventory",
        "write_semantic_registry_bundle",
    }:
        from . import semantic_registry as module
        return getattr(module, name)

    if name in {
        "A04RuntimePreflightRecord",
        "PREFLIGHT_SCHEMA_VERSION",
        "default_preflight_dir",
        "ensure_preflight",
        "make_preflight_record",
        "preflight_path",
        "write_preflight",
    }:
        from . import preflight as module
        return getattr(module, name)

    raise AttributeError(name)
