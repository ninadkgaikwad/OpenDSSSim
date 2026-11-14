"""Persistent circuit-inventory construction, validation, and atomic I/O."""

from __future__ import annotations

import json
import os
import re
import tempfile
from hashlib import sha256
from pathlib import Path

from opendsssim.discovery.native_controls import (
    NATIVE_CONTROL_CLASSES,
    discover_native_controls,
)
from opendsssim.discovery.schema import CircuitDiscovery, DISCOVERY_SCHEMA_VERSION
from opendsssim.network.loading import CircuitSource
from opendsssim.persistence.inventory_schema import (
    CONTROL_RELATIONSHIP_SCHEMA_VERSION,
    INVENTORY_SCHEMA_VERSION,
    CircuitInventory,
    InventoryBus,
    InventoryClass,
    InventoryElement,
    InventoryObject,
)


class CircuitInventoryError(RuntimeError):
    """Base persistent inventory error."""


class CircuitInventoryInvalidError(CircuitInventoryError):
    """Raised when a persisted inventory does not match current inputs."""


def default_inventory_dir() -> Path:
    """Return a stable machine-local cache directory outside circuit sources."""

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "OpenDSSSim" / "inventory"
    return Path.home() / ".opendsssim" / "inventory"


def _safe_stem(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    return cleaned or "circuit"


def inventory_cache_key(
    source: CircuitSource,
    *,
    backend: str,
    altdss_version: str,
    engine_version: str,
) -> str:
    payload = {
        "inventory_schema_version": INVENTORY_SCHEMA_VERSION,
        "relationship_schema_version": CONTROL_RELATIONSHIP_SCHEMA_VERSION,
        "discovery_schema_version": DISCOVERY_SCHEMA_VERSION,
        "backend": backend,
        "altdss_version": altdss_version,
        "engine_version": engine_version,
        "master_relative_path": source.master_relative_path,
        "source_tree_sha256": source.source_tree_sha256,
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest().upper()


def inventory_path_for_source(
    source: CircuitSource,
    *,
    backend: str,
    altdss_version: str,
    engine_version: str,
    inventory_dir: str | Path | None = None,
) -> Path:
    root = (
        Path(inventory_dir).expanduser().resolve()
        if inventory_dir is not None
        else default_inventory_dir()
    )
    key = inventory_cache_key(
        source,
        backend=backend,
        altdss_version=altdss_version,
        engine_version=engine_version,
    )
    stem = _safe_stem(Path(source.master_relative_path).stem)
    return root / f"{stem}__{key[:24]}.json"


def build_circuit_inventory(
    discovery: CircuitDiscovery,
    source: CircuitSource,
    *,
    backend: str,
) -> CircuitInventory:
    """Build static machine-readable inventory from one A02 discovery snapshot."""

    controls, relationships = discover_native_controls(discovery)

    return CircuitInventory(
        schema_version=INVENTORY_SCHEMA_VERSION,
        relationship_schema_version=CONTROL_RELATIONSHIP_SCHEMA_VERSION,
        discovery_schema_version=DISCOVERY_SCHEMA_VERSION,
        backend=backend,
        altdss_version=discovery.engine.altdss_version,
        engine_version=discovery.engine.engine_version,
        master_relative_path=source.master_relative_path,
        master_sha256=source.sha256,
        source_tree_sha256=source.source_tree_sha256,
        source_dependencies=tuple(
            dependency.to_dict() for dependency in source.dependencies
        ),
        circuit_name=discovery.circuit_name,
        num_buses=discovery.num_buses,
        num_nodes=discovery.num_nodes,
        num_circuit_elements=discovery.num_circuit_elements,
        a02_discovery_semantic_sha256=discovery.semantic_sha256,
        buses=tuple(
            InventoryBus(name=item.name, node_names=item.node_names)
            for item in discovery.buses
        ),
        node_names=discovery.node_names,
        classes=tuple(
            InventoryClass(
                dss_class=item.dss_class,
                object_full_names=item.object_full_names,
            )
            for item in discovery.classes
        ),
        objects=tuple(
            InventoryObject(
                full_name=item.full_name,
                dss_class=item.dss_class,
                name=item.name,
                is_circuit_element=item.is_circuit_element,
                property_names=item.property_names,
            )
            for item in discovery.objects
        ),
        elements=tuple(
            InventoryElement(
                full_name=item.full_name,
                dss_class=item.dss_class,
                name=item.name,
                num_phases=item.num_phases,
                num_terminals=item.num_terminals,
                num_conductors=item.num_conductors,
                node_order=item.node_order,
                node_ref=item.node_ref,
                terminal_bus_specs=item.terminal_bus_specs,
                has_switch_control=item.has_switch_control,
                has_volt_control=item.has_volt_control,
                has_ocp_device=item.has_ocp_device,
            )
            for item in discovery.elements
        ),
        native_control_catalog=NATIVE_CONTROL_CLASSES,
        native_controls=controls,
        control_relationships=relationships,
    )


def write_circuit_inventory(
    destination: str | Path,
    inventory: CircuitInventory,
) -> Path:
    """Atomically write one deterministic inventory JSON artifact."""

    destination = Path(destination).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(
        prefix=destination.name + ".",
        suffix=".tmp",
        dir=str(destination.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(inventory.to_json())
        os.replace(tmp_name, destination)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise

    return destination


def read_circuit_inventory(path: str | Path) -> CircuitInventory:
    path = Path(path).expanduser().resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise CircuitInventoryInvalidError(
            f"Expected inventory JSON object: {path}"
        )
    try:
        return CircuitInventory.from_dict(payload)
    except (KeyError, TypeError, ValueError) as exc:
        raise CircuitInventoryInvalidError(
            f"Invalid circuit inventory: {path}"
        ) from exc


def validate_inventory_for_source(
    inventory: CircuitInventory,
    source: CircuitSource,
    *,
    backend: str,
    altdss_version: str,
    engine_version: str,
) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []

    checks = {
        "inventory_schema_version": (
            inventory.schema_version,
            INVENTORY_SCHEMA_VERSION,
        ),
        "relationship_schema_version": (
            inventory.relationship_schema_version,
            CONTROL_RELATIONSHIP_SCHEMA_VERSION,
        ),
        "discovery_schema_version": (
            inventory.discovery_schema_version,
            DISCOVERY_SCHEMA_VERSION,
        ),
        "backend": (inventory.backend, backend),
        "altdss_version": (inventory.altdss_version, altdss_version),
        "engine_version": (inventory.engine_version, engine_version),
        "master_relative_path": (
            inventory.master_relative_path,
            source.master_relative_path,
        ),
        "master_sha256": (inventory.master_sha256, source.sha256),
        "source_tree_sha256": (
            inventory.source_tree_sha256,
            source.source_tree_sha256,
        ),
    }

    for name, (actual, expected) in checks.items():
        if actual != expected:
            reasons.append(
                f"{name}: expected={expected!r} actual={actual!r}"
            )

    dependency_payload = tuple(
        dependency.to_dict() for dependency in source.dependencies
    )
    if inventory.source_dependencies != dependency_payload:
        reasons.append("source_dependencies: dependency manifest changed")

    return (not reasons), tuple(reasons)


def load_valid_inventory(
    source: CircuitSource,
    *,
    backend: str,
    altdss_version: str,
    engine_version: str,
    inventory_dir: str | Path | None = None,
) -> tuple[CircuitInventory | None, Path, tuple[str, ...]]:
    path = inventory_path_for_source(
        source,
        backend=backend,
        altdss_version=altdss_version,
        engine_version=engine_version,
        inventory_dir=inventory_dir,
    )

    if not path.exists():
        return None, path, ("inventory_missing",)

    inventory = read_circuit_inventory(path)
    valid, reasons = validate_inventory_for_source(
        inventory,
        source,
        backend=backend,
        altdss_version=altdss_version,
        engine_version=engine_version,
    )
    if not valid:
        return None, path, reasons

    return inventory, path, ()
