"""Immutable semantic-registry schemas for OpenDSSSim A03."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Mapping, TypeAlias

SEMANTIC_REGISTRY_SCHEMA_VERSION = "A03.semantic-registry.v1"
SEMANTIC_POLICY_VERSION = "A03.semantic-policy.v1+s06.general-capabilities.v1"


class Mutability(str, Enum):
    READ_ONLY = "READ_ONLY"
    INIT_ONLY = "INIT_ONLY"
    STEP_CONTROLLABLE = "STEP_CONTROLLABLE"
    STEP_EXOGENOUS = "STEP_EXOGENOUS"


@dataclass(frozen=True)
class NativePropertyAddress:
    object_full_name: str
    property_name: str

    @property
    def kind(self) -> str:
        return "NATIVE_PROPERTY"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "object_full_name": self.object_full_name,
            "property_name": self.property_name,
        }


@dataclass(frozen=True)
class RuntimeReadoutAddress:
    service: str
    entity: str | None
    channel: str

    @property
    def kind(self) -> str:
        return "RUNTIME_READOUT"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "service": self.service,
            "entity": self.entity,
            "channel": self.channel,
        }


@dataclass(frozen=True)
class RuntimeCommandAddress:
    service: str
    entity: str
    operation: str

    @property
    def kind(self) -> str:
        return "RUNTIME_COMMAND"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "service": self.service,
            "entity": self.entity,
            "operation": self.operation,
        }


SemanticAddress: TypeAlias = (
    NativePropertyAddress | RuntimeReadoutAddress | RuntimeCommandAddress
)


def address_from_dict(payload: Mapping[str, Any]) -> SemanticAddress:
    kind = str(payload["kind"])
    if kind == "NATIVE_PROPERTY":
        return NativePropertyAddress(
            object_full_name=str(payload["object_full_name"]),
            property_name=str(payload["property_name"]),
        )
    if kind == "RUNTIME_READOUT":
        entity = payload.get("entity")
        return RuntimeReadoutAddress(
            service=str(payload["service"]),
            entity=None if entity is None else str(entity),
            channel=str(payload["channel"]),
        )
    if kind == "RUNTIME_COMMAND":
        return RuntimeCommandAddress(
            service=str(payload["service"]),
            entity=str(payload["entity"]),
            operation=str(payload["operation"]),
        )
    raise ValueError(f"Unknown semantic address kind: {kind}")


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _sorted_unique(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(sorted(set(str(value) for value in values), key=str.casefold))


@dataclass(frozen=True)
class SemanticEntry:
    semantic_id: str
    address: SemanticAddress
    native_entity: str | None
    quantity: str
    unit: str | None
    dtype: str
    shape: tuple[int, ...]
    selectors: tuple[tuple[str, str], ...]
    mutability: Mutability
    static_metadata: tuple[tuple[str, str], ...]
    capability_tags: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "semantic_id": self.semantic_id,
            "address": self.address.to_dict(),
            "native_entity": self.native_entity,
            "quantity": self.quantity,
            "unit": self.unit,
            "dtype": self.dtype,
            "shape": list(self.shape),
            "selectors": [[key, value] for key, value in self.selectors],
            "mutability": self.mutability.value,
            "static_metadata": [
                [key, value_json] for key, value_json in self.static_metadata
            ],
            "capability_tags": list(self.capability_tags),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SemanticEntry":
        return cls(
            semantic_id=str(payload["semantic_id"]),
            address=address_from_dict(payload["address"]),
            native_entity=(
                None
                if payload.get("native_entity") is None
                else str(payload["native_entity"])
            ),
            quantity=str(payload["quantity"]),
            unit=None if payload.get("unit") is None else str(payload["unit"]),
            dtype=str(payload["dtype"]),
            shape=tuple(int(value) for value in payload.get("shape", [])),
            selectors=tuple(
                (str(item[0]), str(item[1]))
                for item in payload.get("selectors", [])
            ),
            mutability=Mutability(str(payload["mutability"])),
            static_metadata=tuple(
                (str(item[0]), str(item[1]))
                for item in payload.get("static_metadata", [])
            ),
            capability_tags=tuple(
                str(value) for value in payload.get("capability_tags", [])
            ),
        )

    def metadata_dict(self) -> dict[str, Any]:
        return {
            key: json.loads(value_json)
            for key, value_json in self.static_metadata
        }


@dataclass(frozen=True)
class RegistryView:
    entry_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"entry_ids": list(self.entry_ids)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RegistryView":
        return cls(entry_ids=tuple(str(value) for value in payload["entry_ids"]))


@dataclass(frozen=True)
class StateRegistry(RegistryView):
    pass


@dataclass(frozen=True)
class ActionRegistry(RegistryView):
    pass


@dataclass(frozen=True)
class DisturbanceRegistry(RegistryView):
    pass


@dataclass(frozen=True)
class ConstraintRegistry(RegistryView):
    pass


@dataclass(frozen=True)
class ParameterRegistry(RegistryView):
    pass


@dataclass(frozen=True)
class CircuitClassRecord:
    dss_class: str
    object_full_names: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dss_class": self.dss_class,
            "object_full_names": list(self.object_full_names),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CircuitClassRecord":
        return cls(
            dss_class=str(payload["dss_class"]),
            object_full_names=tuple(
                str(value) for value in payload["object_full_names"]
            ),
        )


@dataclass(frozen=True)
class CircuitRelationshipRecord:
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_full_name": self.source_full_name,
            "source_class": self.source_class,
            "role": self.role,
            "property_name": self.property_name,
            "target_reference": self.target_reference,
            "target_full_name": self.target_full_name,
            "target_kind": self.target_kind,
            "resolution": self.resolution,
            "terminal": self.terminal,
            "winding": self.winding,
            "tap_winding": self.tap_winding,
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> "CircuitRelationshipRecord":
        return cls(
            source_full_name=str(payload["source_full_name"]),
            source_class=str(payload["source_class"]),
            role=str(payload["role"]),
            property_name=str(payload["property_name"]),
            target_reference=str(payload["target_reference"]),
            target_full_name=(
                None
                if payload.get("target_full_name") is None
                else str(payload["target_full_name"])
            ),
            target_kind=str(payload["target_kind"]),
            resolution=str(payload["resolution"]),
            terminal=(
                None
                if payload.get("terminal") is None
                else int(payload["terminal"])
            ),
            winding=(
                None
                if payload.get("winding") is None
                else int(payload["winding"])
            ),
            tap_winding=(
                None
                if payload.get("tap_winding") is None
                else int(payload["tap_winding"])
            ),
        )


@dataclass(frozen=True)
class CircuitRegistry:
    circuit_name: str
    bus_names: tuple[str, ...]
    node_names: tuple[str, ...]
    classes: tuple[CircuitClassRecord, ...]
    object_full_names: tuple[str, ...]
    control_relationships: tuple[CircuitRelationshipRecord, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "circuit_name": self.circuit_name,
            "bus_names": list(self.bus_names),
            "node_names": list(self.node_names),
            "classes": [item.to_dict() for item in self.classes],
            "object_full_names": list(self.object_full_names),
            "control_relationships": [
                item.to_dict() for item in self.control_relationships
            ],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CircuitRegistry":
        return cls(
            circuit_name=str(payload["circuit_name"]),
            bus_names=tuple(str(value) for value in payload["bus_names"]),
            node_names=tuple(str(value) for value in payload["node_names"]),
            classes=tuple(
                CircuitClassRecord.from_dict(item)
                for item in payload["classes"]
            ),
            object_full_names=tuple(
                str(value) for value in payload["object_full_names"]
            ),
            control_relationships=tuple(
                CircuitRelationshipRecord.from_dict(item)
                for item in payload["control_relationships"]
            ),
        )


@dataclass(frozen=True)
class CapabilityRecord:
    capability_id: str
    evidence_entry_ids: tuple[str, ...]
    evidence_native_entities: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "evidence_entry_ids": list(self.evidence_entry_ids),
            "evidence_native_entities": list(self.evidence_native_entities),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CapabilityRecord":
        return cls(
            capability_id=str(payload["capability_id"]),
            evidence_entry_ids=tuple(
                str(value) for value in payload["evidence_entry_ids"]
            ),
            evidence_native_entities=tuple(
                str(value) for value in payload["evidence_native_entities"]
            ),
        )


@dataclass(frozen=True)
class CapabilityRegistry:
    capabilities: tuple[CapabilityRecord, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "capabilities": [item.to_dict() for item in self.capabilities]
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CapabilityRegistry":
        return cls(
            capabilities=tuple(
                CapabilityRecord.from_dict(item)
                for item in payload["capabilities"]
            )
        )

    @property
    def capability_ids(self) -> tuple[str, ...]:
        return tuple(item.capability_id for item in self.capabilities)

    def has(self, capability_id: str) -> bool:
        return capability_id in set(self.capability_ids)


@dataclass(frozen=True)
class SemanticRegistryBundle:
    registry_schema_version: str
    semantic_policy_version: str
    semantic_policy_sha256: str
    source_inventory_semantic_sha256: str
    source_tree_sha256: str
    backend: str
    altdss_version: str
    engine_version: str
    semantic_entries: tuple[SemanticEntry, ...]
    circuit_registry: CircuitRegistry
    state_registry: StateRegistry
    action_registry: ActionRegistry
    disturbance_registry: DisturbanceRegistry
    constraint_registry: ConstraintRegistry
    parameter_registry: ParameterRegistry
    capability_registry: CapabilityRegistry

    def semantic_dict(self) -> dict[str, Any]:
        return {
            "registry_schema_version": self.registry_schema_version,
            "semantic_policy_version": self.semantic_policy_version,
            "semantic_policy_sha256": self.semantic_policy_sha256,
            "source_inventory_semantic_sha256": (
                self.source_inventory_semantic_sha256
            ),
            "source_tree_sha256": self.source_tree_sha256,
            "backend": self.backend,
            "altdss_version": self.altdss_version,
            "engine_version": self.engine_version,
            "semantic_entries": [
                item.to_dict() for item in self.semantic_entries
            ],
            "circuit_registry": self.circuit_registry.to_dict(),
            "state_registry": self.state_registry.to_dict(),
            "action_registry": self.action_registry.to_dict(),
            "disturbance_registry": self.disturbance_registry.to_dict(),
            "constraint_registry": self.constraint_registry.to_dict(),
            "parameter_registry": self.parameter_registry.to_dict(),
            "capability_registry": self.capability_registry.to_dict(),
        }

    @property
    def semantic_sha256(self) -> str:
        encoded = canonical_json(self.semantic_dict()).encode("utf-8")
        return sha256(encoded).hexdigest().upper()

    def to_serialized_dict(self) -> dict[str, Any]:
        payload = self.semantic_dict()
        payload["bundle_semantic_sha256"] = self.semantic_sha256
        return payload

    def to_json(self) -> str:
        return json.dumps(
            self.to_serialized_dict(),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        ) + "\n"

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SemanticRegistryBundle":
        supplied_hash = payload.get("bundle_semantic_sha256")
        bundle = cls(
            registry_schema_version=str(payload["registry_schema_version"]),
            semantic_policy_version=str(payload["semantic_policy_version"]),
            semantic_policy_sha256=str(payload["semantic_policy_sha256"]),
            source_inventory_semantic_sha256=str(
                payload["source_inventory_semantic_sha256"]
            ),
            source_tree_sha256=str(payload["source_tree_sha256"]),
            backend=str(payload["backend"]),
            altdss_version=str(payload["altdss_version"]),
            engine_version=str(payload["engine_version"]),
            semantic_entries=tuple(
                SemanticEntry.from_dict(item)
                for item in payload["semantic_entries"]
            ),
            circuit_registry=CircuitRegistry.from_dict(
                payload["circuit_registry"]
            ),
            state_registry=StateRegistry.from_dict(payload["state_registry"]),
            action_registry=ActionRegistry.from_dict(payload["action_registry"]),
            disturbance_registry=DisturbanceRegistry.from_dict(
                payload["disturbance_registry"]
            ),
            constraint_registry=ConstraintRegistry.from_dict(
                payload["constraint_registry"]
            ),
            parameter_registry=ParameterRegistry.from_dict(
                payload["parameter_registry"]
            ),
            capability_registry=CapabilityRegistry.from_dict(
                payload["capability_registry"]
            ),
        )
        if (
            supplied_hash is not None
            and str(supplied_hash) != bundle.semantic_sha256
        ):
            raise ValueError(
                "SemanticRegistryBundle semantic SHA256 mismatch. "
                f"expected={supplied_hash} actual={bundle.semantic_sha256}"
            )
        return bundle

    def entry_by_id(self) -> dict[str, SemanticEntry]:
        return {item.semantic_id: item for item in self.semantic_entries}


def deterministic_semantic_id(
    address: SemanticAddress,
    quantity: str,
    selectors: tuple[tuple[str, str], ...] = (),
) -> str:
    payload = {
        "address": address.to_dict(),
        "quantity": str(quantity),
        "selectors": [[str(k), str(v)] for k, v in selectors],
    }
    digest = sha256(canonical_json(payload).encode("utf-8")).hexdigest().upper()
    return f"sem:{digest[:24]}"


def normalize_string_tuple(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return _sorted_unique(values)
