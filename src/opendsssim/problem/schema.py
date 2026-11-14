"""Immutable A04 problem-contract schemas.

A04 selects and organizes semantics that already exist in the A03
SemanticRegistryBundle.  It never invents native OpenDSS addresses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Mapping, TypeAlias

from opendsssim.semantics.schema import Mutability, canonical_json

PROBLEM_SCHEMA_VERSION = "A04.problem.v1"
RESOLVED_PROBLEM_SCHEMA_VERSION = "A04.resolved-problem.v1"
GYM_SPACE_SCHEMA_VERSION = "A04.gym-space.v1"


def _canonical_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, tuple):
        return [_canonical_value(item) for item in value]
    if isinstance(value, list):
        return [_canonical_value(item) for item in value]
    if isinstance(value, Mapping):
        return {
            str(key): _canonical_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    return value


def _hash_payload(payload: Mapping[str, Any]) -> str:
    encoded = canonical_json(_canonical_value(payload)).encode("utf-8")
    return sha256(encoded).hexdigest().upper()


def _metadata_pairs(metadata: Mapping[str, Any] | None) -> tuple[tuple[str, str], ...]:
    if not metadata:
        return ()
    return tuple(
        (
            str(key),
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        )
        for key, value in sorted(metadata.items(), key=lambda pair: str(pair[0]).casefold())
    )


def metadata_dict(pairs: tuple[tuple[str, str], ...]) -> dict[str, Any]:
    return {key: json.loads(value_json) for key, value_json in pairs}


class RegistryKind(str, Enum):
    STATE = "state"
    ACTION = "action"
    DISTURBANCE = "disturbance"
    CONSTRAINT = "constraint"
    PARAMETER = "parameter"


class CardinalityKind(str, Enum):
    ANY = "ANY"
    NONEMPTY = "NONEMPTY"
    EXACT = "EXACT"
    RANGE = "RANGE"


@dataclass(frozen=True)
class CardinalityRequirement:
    kind: CardinalityKind = CardinalityKind.ANY
    exact: int | None = None
    minimum: int | None = None
    maximum: int | None = None

    def __post_init__(self) -> None:
        if self.kind is CardinalityKind.EXACT:
            if self.exact is None or self.exact < 0:
                raise ValueError("EXACT cardinality requires exact >= 0.")
            if self.minimum is not None or self.maximum is not None:
                raise ValueError("EXACT cardinality cannot also define RANGE bounds.")
        elif self.kind is CardinalityKind.RANGE:
            if self.minimum is None or self.maximum is None:
                raise ValueError("RANGE cardinality requires minimum and maximum.")
            if self.minimum < 0 or self.maximum < self.minimum:
                raise ValueError("Invalid RANGE cardinality bounds.")
            if self.exact is not None:
                raise ValueError("RANGE cardinality cannot define exact.")
        elif any(value is not None for value in (self.exact, self.minimum, self.maximum)):
            raise ValueError(f"{self.kind.value} cardinality does not take numeric bounds.")

    def validate(self, count: int, *, label: str) -> None:
        if self.kind is CardinalityKind.ANY:
            return
        if self.kind is CardinalityKind.NONEMPTY and count < 1:
            raise ValueError(f"Cardinality failure for {label}: expected NONEMPTY, got {count}.")
        if self.kind is CardinalityKind.EXACT and count != self.exact:
            raise ValueError(
                f"Cardinality failure for {label}: expected EXACT({self.exact}), got {count}."
            )
        if self.kind is CardinalityKind.RANGE and not (self.minimum <= count <= self.maximum):
            raise ValueError(
                f"Cardinality failure for {label}: expected RANGE({self.minimum},{self.maximum}), got {count}."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "exact": self.exact,
            "minimum": self.minimum,
            "maximum": self.maximum,
        }


ANY_CARDINALITY = CardinalityRequirement()
NONEMPTY_CARDINALITY = CardinalityRequirement(CardinalityKind.NONEMPTY)


@dataclass(frozen=True)
class ExactSemanticRef:
    registry: RegistryKind
    semantic_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "exact",
            "registry": self.registry.value,
            "semantic_id": self.semantic_id,
        }


@dataclass(frozen=True)
class SemanticQuery:
    registry: RegistryKind
    dss_class: str | None = None
    object_name: str | None = None
    native_entity: str | None = None
    quantity: str | None = None
    mutability: Mutability | None = None
    selectors: tuple[tuple[str, str], ...] = ()
    capability_tags: tuple[str, ...] = ()
    cardinality: CardinalityRequirement = field(default_factory=CardinalityRequirement)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "query",
            "registry": self.registry.value,
            "dss_class": self.dss_class,
            "object_name": self.object_name,
            "native_entity": self.native_entity,
            "quantity": self.quantity,
            "mutability": None if self.mutability is None else self.mutability.value,
            "selectors": [[key, value] for key, value in self.selectors],
            "capability_tags": list(self.capability_tags),
            "cardinality": self.cardinality.to_dict(),
        }


SemanticSelection: TypeAlias = ExactSemanticRef | SemanticQuery


class OrderingPolicy(str, Enum):
    AUTHORED_THEN_CANONICAL = "AUTHORED_THEN_CANONICAL"


@dataclass(frozen=True)
class ActionRestriction:
    low: float | None = None
    high: float | None = None
    allowed_values: tuple[str | int | float, ...] = ()
    shape: tuple[int, ...] | None = None

    def __post_init__(self) -> None:
        if self.low is not None and self.high is not None and self.high < self.low:
            raise ValueError("ActionRestriction high must be >= low.")
        if self.shape is not None and any(value < 1 for value in self.shape):
            raise ValueError("ActionRestriction shape entries must be positive.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "low": self.low,
            "high": self.high,
            "allowed_values": list(self.allowed_values),
            "shape": None if self.shape is None else list(self.shape),
        }


@dataclass(frozen=True)
class SelectionGroup:
    group_id: str
    selections: tuple[SemanticSelection, ...]
    cardinality: CardinalityRequirement = field(default_factory=CardinalityRequirement)
    ordering_policy: OrderingPolicy = OrderingPolicy.AUTHORED_THEN_CANONICAL
    action_restriction: ActionRestriction | None = None

    def __post_init__(self) -> None:
        if not self.group_id.strip():
            raise ValueError("SelectionGroup.group_id must be non-empty.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "selections": [item.to_dict() for item in self.selections],
            "cardinality": self.cardinality.to_dict(),
            "ordering_policy": self.ordering_policy.value,
            "action_restriction": (
                None if self.action_restriction is None else self.action_restriction.to_dict()
            ),
        }


@dataclass(frozen=True)
class ObservationSpec:
    groups: tuple[SelectionGroup, ...] = ()
    forecast_groups: tuple[SelectionGroup, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "groups": [group.to_dict() for group in self.groups],
            "forecast_groups": [group.to_dict() for group in self.forecast_groups],
        }


@dataclass(frozen=True)
class ActionSpec:
    groups: tuple[SelectionGroup, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"groups": [group.to_dict() for group in self.groups]}


@dataclass(frozen=True)
class RegistrySelectionSpec:
    groups: tuple[SelectionGroup, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"groups": [group.to_dict() for group in self.groups]}


@dataclass(frozen=True)
class CapabilityRequirement:
    capability_id: str
    required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {"capability_id": self.capability_id, "required": self.required}


@dataclass(frozen=True)
class DeviceRef:
    full_name: str

    def to_dict(self) -> dict[str, Any]:
        return {"type": "exact", "full_name": self.full_name}


@dataclass(frozen=True)
class DeviceQuery:
    dss_class: str | None = None
    object_name: str | None = None
    cardinality: CardinalityRequirement = field(default_factory=CardinalityRequirement)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "query",
            "dss_class": self.dss_class,
            "object_name": self.object_name,
            "cardinality": self.cardinality.to_dict(),
        }


DeviceSelection: TypeAlias = DeviceRef | DeviceQuery


@dataclass(frozen=True)
class FaultSpec:
    fault_id: str
    targets: tuple[DeviceSelection, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "fault_id": self.fault_id,
            "targets": [target.to_dict() for target in self.targets],
        }


class ControlAuthorityMode(str, Enum):
    NATIVE = "NATIVE"
    EXTERNAL = "EXTERNAL"
    HYBRID = "HYBRID"


@dataclass(frozen=True)
class ControlAuthoritySpec:
    mode: ControlAuthorityMode = ControlAuthorityMode.NATIVE
    native_entities: tuple[str, ...] = ()
    external_entities: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "native_entities": list(self.native_entities),
            "external_entities": list(self.external_entities),
        }


class HookMode(str, Enum):
    DEFAULT = "DEFAULT"
    IMPORT = "IMPORT"


@dataclass(frozen=True)
class HookSpec:
    mode: HookMode = HookMode.DEFAULT
    module: str | None = None
    qualname: str | None = None
    source_sha256: str | None = None
    config: tuple[tuple[str, str], ...] = ()

    @classmethod
    def imported(
        cls,
        module: str,
        qualname: str,
        *,
        source_sha256: str | None = None,
        config: Mapping[str, Any] | None = None,
    ) -> "HookSpec":
        return cls(
            mode=HookMode.IMPORT,
            module=module,
            qualname=qualname,
            source_sha256=source_sha256,
            config=_metadata_pairs(config),
        )

    def __post_init__(self) -> None:
        if self.mode is HookMode.IMPORT and (not self.module or not self.qualname):
            raise ValueError("IMPORT HookSpec requires module and qualname.")
        if self.mode is HookMode.DEFAULT and any(
            item is not None for item in (self.module, self.qualname, self.source_sha256)
        ):
            raise ValueError("DEFAULT HookSpec cannot define imported-callable identity.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "module": self.module,
            "qualname": self.qualname,
            "source_sha256": self.source_sha256,
            "config": [[key, value] for key, value in self.config],
        }


@dataclass(frozen=True)
class ProblemSpec:
    problem_id: str
    problem_version: str
    observations: ObservationSpec = field(default_factory=ObservationSpec)
    actions: ActionSpec = field(default_factory=ActionSpec)
    disturbances: RegistrySelectionSpec = field(default_factory=RegistrySelectionSpec)
    parameters: RegistrySelectionSpec = field(default_factory=RegistrySelectionSpec)
    constraints: RegistrySelectionSpec = field(default_factory=RegistrySelectionSpec)
    capability_requirements: tuple[CapabilityRequirement, ...] = ()
    control_authority: ControlAuthoritySpec = field(default_factory=ControlAuthoritySpec)
    faults: tuple[FaultSpec, ...] = ()
    reward: HookSpec = field(default_factory=HookSpec)
    termination: HookSpec = field(default_factory=HookSpec)
    truncation: HookSpec = field(default_factory=HookSpec)
    metadata: tuple[tuple[str, str], ...] = ()
    schema_version: str = PROBLEM_SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        problem_id: str,
        problem_version: str,
        *,
        metadata: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> "ProblemSpec":
        return cls(
            problem_id=problem_id,
            problem_version=problem_version,
            metadata=_metadata_pairs(metadata),
            **kwargs,
        )

    def __post_init__(self) -> None:
        if not self.problem_id.strip() or not self.problem_version.strip():
            raise ValueError("ProblemSpec requires non-empty problem_id and problem_version.")
        if self.schema_version != PROBLEM_SCHEMA_VERSION:
            raise ValueError(f"Unsupported ProblemSpec schema version: {self.schema_version}")

    def semantic_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "problem_id": self.problem_id,
            "problem_version": self.problem_version,
            "observations": self.observations.to_dict(),
            "actions": self.actions.to_dict(),
            "disturbances": self.disturbances.to_dict(),
            "parameters": self.parameters.to_dict(),
            "constraints": self.constraints.to_dict(),
            "capability_requirements": [item.to_dict() for item in self.capability_requirements],
            "control_authority": self.control_authority.to_dict(),
            "faults": [item.to_dict() for item in self.faults],
            "reward": self.reward.to_dict(),
            "termination": self.termination.to_dict(),
            "truncation": self.truncation.to_dict(),
            "metadata": [[key, value] for key, value in self.metadata],
        }

    @property
    def problem_spec_sha256(self) -> str:
        return _hash_payload(self.semantic_dict())


class SemanticActionKind(str, Enum):
    CONTINUOUS = "CONTINUOUS"
    BINARY = "BINARY"
    CATEGORICAL = "CATEGORICAL"
    ORDERED_INTEGER = "ORDERED_INTEGER"


@dataclass(frozen=True)
class ResolvedChannel:
    semantic_id: str
    source_registry: RegistryKind
    native_entity: str | None
    dss_class: str
    object_name: str
    quantity: str
    unit: str | None
    dtype: str
    native_shape: tuple[int, ...]
    selectors: tuple[tuple[str, str], ...]
    address_kind: str
    capability_tags: tuple[str, ...]
    action_kind: SemanticActionKind | None = None
    static_low: float | None = None
    static_high: float | None = None
    allowed_values: tuple[str | int | float, ...] = ()
    resolved_shape: tuple[int, ...] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "semantic_id": self.semantic_id,
            "source_registry": self.source_registry.value,
            "native_entity": self.native_entity,
            "dss_class": self.dss_class,
            "object_name": self.object_name,
            "quantity": self.quantity,
            "unit": self.unit,
            "dtype": self.dtype,
            "native_shape": list(self.native_shape),
            "selectors": [[key, value] for key, value in self.selectors],
            "address_kind": self.address_kind,
            "capability_tags": list(self.capability_tags),
            "action_kind": None if self.action_kind is None else self.action_kind.value,
            "static_low": self.static_low,
            "static_high": self.static_high,
            "allowed_values": list(self.allowed_values),
            "resolved_shape": None if self.resolved_shape is None else list(self.resolved_shape),
        }


@dataclass(frozen=True)
class ResolvedSelectionGroup:
    group_id: str
    channels: tuple[ResolvedChannel, ...]
    action_restriction: ActionRestriction | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "channels": [channel.to_dict() for channel in self.channels],
            "resolved_count": len(self.channels),
            "action_restriction": (
                None if self.action_restriction is None else self.action_restriction.to_dict()
            ),
        }


@dataclass(frozen=True)
class ResolvedObservationSpec:
    groups: tuple[ResolvedSelectionGroup, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"groups": [group.to_dict() for group in self.groups]}


@dataclass(frozen=True)
class ResolvedActionSpec:
    groups: tuple[ResolvedSelectionGroup, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"groups": [group.to_dict() for group in self.groups]}


@dataclass(frozen=True)
class ResolvedRegistrySelectionSpec:
    groups: tuple[ResolvedSelectionGroup, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"groups": [group.to_dict() for group in self.groups]}


@dataclass(frozen=True)
class ResolvedFaultSpec:
    fault_id: str
    target_full_names: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "fault_id": self.fault_id,
            "target_full_names": list(self.target_full_names),
        }


@dataclass(frozen=True)
class ResolvedControlAuthoritySpec:
    mode: ControlAuthorityMode
    native_entities: tuple[str, ...]
    external_entities: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "native_entities": list(self.native_entities),
            "external_entities": list(self.external_entities),
        }


@dataclass(frozen=True)
class ResolvedProblemSpec:
    authored_problem_spec_sha256: str
    source_semantic_bundle_sha256: str
    source_inventory_semantic_sha256: str
    source_tree_sha256: str
    problem_id: str
    problem_version: str
    observations: ResolvedObservationSpec
    actions: ResolvedActionSpec
    disturbances: ResolvedRegistrySelectionSpec
    parameters: ResolvedRegistrySelectionSpec
    constraints: ResolvedRegistrySelectionSpec
    satisfied_capabilities: tuple[str, ...]
    control_authority: ResolvedControlAuthoritySpec
    faults: tuple[ResolvedFaultSpec, ...]
    reward: HookSpec
    termination: HookSpec
    truncation: HookSpec
    metadata: tuple[tuple[str, str], ...]
    schema_version: str = RESOLVED_PROBLEM_SCHEMA_VERSION

    def semantic_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "authored_problem_spec_sha256": self.authored_problem_spec_sha256,
            "source_semantic_bundle_sha256": self.source_semantic_bundle_sha256,
            "source_inventory_semantic_sha256": self.source_inventory_semantic_sha256,
            "source_tree_sha256": self.source_tree_sha256,
            "problem_id": self.problem_id,
            "problem_version": self.problem_version,
            "observations": self.observations.to_dict(),
            "actions": self.actions.to_dict(),
            "disturbances": self.disturbances.to_dict(),
            "parameters": self.parameters.to_dict(),
            "constraints": self.constraints.to_dict(),
            "satisfied_capabilities": list(self.satisfied_capabilities),
            "control_authority": self.control_authority.to_dict(),
            "faults": [fault.to_dict() for fault in self.faults],
            "reward": self.reward.to_dict(),
            "termination": self.termination.to_dict(),
            "truncation": self.truncation.to_dict(),
            "metadata": [[key, value] for key, value in self.metadata],
        }

    @property
    def resolved_problem_sha256(self) -> str:
        return _hash_payload(self.semantic_dict())
