"""Immutable machine-readable circuit inventory schemas for A02H1."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Any

INVENTORY_SCHEMA_VERSION = "A02H1.inventory.v1"
CONTROL_RELATIONSHIP_SCHEMA_VERSION = "A02H1.control-relations.v1"


@dataclass(frozen=True)
class InventoryBus:
    name: str
    node_names: tuple[str, ...]


@dataclass(frozen=True)
class InventoryClass:
    dss_class: str
    object_full_names: tuple[str, ...]


@dataclass(frozen=True)
class InventoryObject:
    full_name: str
    dss_class: str
    name: str
    is_circuit_element: bool
    property_names: tuple[str, ...]


@dataclass(frozen=True)
class InventoryElement:
    full_name: str
    dss_class: str
    name: str
    num_phases: int
    num_terminals: int
    num_conductors: int
    node_order: tuple[int, ...]
    node_ref: tuple[int, ...]
    terminal_bus_specs: tuple[str, ...]
    has_switch_control: bool
    has_volt_control: bool
    has_ocp_device: bool


@dataclass(frozen=True)
class NativeControlObject:
    full_name: str
    dss_class: str
    name: str
    property_names: tuple[str, ...]


@dataclass(frozen=True)
class NativeControlRelationship:
    source_full_name: str
    source_class: str
    role: str
    property_name: str
    target_reference: str
    target_full_name: str | None
    target_kind: str
    resolution: str
    terminal: int | None = None
    winding: int | None = None
    tap_winding: int | None = None


@dataclass(frozen=True)
class CircuitInventory:
    """Persistent static description of one compiled circuit configuration."""

    schema_version: str
    relationship_schema_version: str
    discovery_schema_version: str
    backend: str
    altdss_version: str
    engine_version: str
    master_relative_path: str
    master_sha256: str
    source_tree_sha256: str
    source_dependencies: tuple[dict[str, Any], ...]
    circuit_name: str
    num_buses: int
    num_nodes: int
    num_circuit_elements: int
    a02_discovery_semantic_sha256: str
    buses: tuple[InventoryBus, ...]
    node_names: tuple[str, ...]
    classes: tuple[InventoryClass, ...]
    objects: tuple[InventoryObject, ...]
    elements: tuple[InventoryElement, ...]
    native_control_catalog: tuple[str, ...]
    native_controls: tuple[NativeControlObject, ...]
    control_relationships: tuple[NativeControlRelationship, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def static_semantic_dict(self) -> dict[str, Any]:
        """Return static content excluding the build-time A02 discovery hash."""

        payload = self.to_dict()
        payload.pop("a02_discovery_semantic_sha256", None)
        return payload

    @property
    def semantic_sha256(self) -> str:
        encoded = json.dumps(
            self.static_semantic_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return sha256(encoded).hexdigest().upper()

    def to_serialized_dict(self) -> dict[str, Any]:
        payload = self.to_dict()
        payload["semantic_sha256"] = self.semantic_sha256
        return payload

    def to_json(self) -> str:
        return json.dumps(
            self.to_serialized_dict(),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        ) + "\n"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CircuitInventory":
        supplied_hash = payload.get("semantic_sha256")

        inventory = cls(
            schema_version=str(payload["schema_version"]),
            relationship_schema_version=str(payload["relationship_schema_version"]),
            discovery_schema_version=str(payload["discovery_schema_version"]),
            backend=str(payload["backend"]),
            altdss_version=str(payload["altdss_version"]),
            engine_version=str(payload["engine_version"]),
            master_relative_path=str(payload["master_relative_path"]),
            master_sha256=str(payload["master_sha256"]),
            source_tree_sha256=str(payload["source_tree_sha256"]),
            source_dependencies=tuple(
                dict(item) for item in payload["source_dependencies"]
            ),
            circuit_name=str(payload["circuit_name"]),
            num_buses=int(payload["num_buses"]),
            num_nodes=int(payload["num_nodes"]),
            num_circuit_elements=int(payload["num_circuit_elements"]),
            a02_discovery_semantic_sha256=str(
                payload["a02_discovery_semantic_sha256"]
            ),
            buses=tuple(
                InventoryBus(
                    name=str(item["name"]),
                    node_names=tuple(str(value) for value in item["node_names"]),
                )
                for item in payload["buses"]
            ),
            node_names=tuple(str(item) for item in payload["node_names"]),
            classes=tuple(
                InventoryClass(
                    dss_class=str(item["dss_class"]),
                    object_full_names=tuple(
                        str(value) for value in item["object_full_names"]
                    ),
                )
                for item in payload["classes"]
            ),
            objects=tuple(
                InventoryObject(
                    full_name=str(item["full_name"]),
                    dss_class=str(item["dss_class"]),
                    name=str(item["name"]),
                    is_circuit_element=bool(item["is_circuit_element"]),
                    property_names=tuple(
                        str(value) for value in item["property_names"]
                    ),
                )
                for item in payload["objects"]
            ),
            elements=tuple(
                InventoryElement(
                    full_name=str(item["full_name"]),
                    dss_class=str(item["dss_class"]),
                    name=str(item["name"]),
                    num_phases=int(item["num_phases"]),
                    num_terminals=int(item["num_terminals"]),
                    num_conductors=int(item["num_conductors"]),
                    node_order=tuple(int(value) for value in item["node_order"]),
                    node_ref=tuple(int(value) for value in item["node_ref"]),
                    terminal_bus_specs=tuple(
                        str(value) for value in item["terminal_bus_specs"]
                    ),
                    has_switch_control=bool(item["has_switch_control"]),
                    has_volt_control=bool(item["has_volt_control"]),
                    has_ocp_device=bool(item["has_ocp_device"]),
                )
                for item in payload["elements"]
            ),
            native_control_catalog=tuple(
                str(item) for item in payload["native_control_catalog"]
            ),
            native_controls=tuple(
                NativeControlObject(
                    full_name=str(item["full_name"]),
                    dss_class=str(item["dss_class"]),
                    name=str(item["name"]),
                    property_names=tuple(
                        str(value) for value in item["property_names"]
                    ),
                )
                for item in payload["native_controls"]
            ),
            control_relationships=tuple(
                NativeControlRelationship(
                    source_full_name=str(item["source_full_name"]),
                    source_class=str(item["source_class"]),
                    role=str(item["role"]),
                    property_name=str(item["property_name"]),
                    target_reference=str(item["target_reference"]),
                    target_full_name=(
                        None
                        if item.get("target_full_name") is None
                        else str(item["target_full_name"])
                    ),
                    target_kind=str(item["target_kind"]),
                    resolution=str(item["resolution"]),
                    terminal=(
                        None
                        if item.get("terminal") is None
                        else int(item["terminal"])
                    ),
                    winding=(
                        None
                        if item.get("winding") is None
                        else int(item["winding"])
                    ),
                    tap_winding=(
                        None
                        if item.get("tap_winding") is None
                        else int(item["tap_winding"])
                    ),
                )
                for item in payload["control_relationships"]
            ),
        )

        if supplied_hash is not None and str(supplied_hash) != inventory.semantic_sha256:
            raise ValueError(
                "CircuitInventory semantic SHA256 mismatch. "
                f"expected={supplied_hash} actual={inventory.semantic_sha256}"
            )

        return inventory
