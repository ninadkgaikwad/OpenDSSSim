"""Immutable A04I3 runtime-binding and step-context schemas."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Callable, Mapping

import numpy as np

from opendsssim.problem.schema import HookSpec, RegistryKind, ResolvedProblemSpec
from opendsssim.problem.spaces import CompiledGymSpaces, SpaceLayoutEntry
from opendsssim.semantics.schema import SemanticEntry


class ActionApplicationStatus(str, Enum):
    ADMISSIBLE_APPLIED = "ADMISSIBLE_APPLIED"
    FAULT_DISABLED = "FAULT_DISABLED"
    AUTHORITY_NATIVE = "AUTHORITY_NATIVE"
    INVALID_GYM_ACTION = "INVALID_GYM_ACTION"
    NONFINITE_ACTION = "NONFINITE_ACTION"
    BACKEND_APPLICATION_ERROR = "BACKEND_APPLICATION_ERROR"


class HistoryLevel(str, Enum):
    H0 = "H0"
    H1 = "H1"
    H2 = "H2"
    H3 = "H3"


class ExecutionProfile(str, Enum):
    FAST = "FAST"
    STANDARD = "STANDARD"
    AUDIT = "AUDIT"


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_value(item) for key, item in value.items()})
    if isinstance(value, np.ndarray):
        array = np.array(value, copy=True)
        array.setflags(write=False)
        return array
    if isinstance(value, (tuple, list)):
        return tuple(_freeze_value(item) for item in value)
    return value


def _readonly_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    frozen = _freeze_value(dict(value or {}))
    assert isinstance(frozen, Mapping)
    return frozen


@dataclass(frozen=True, slots=True)
class RuntimeChannelBinding:
    semantic_id: str
    source_registry: RegistryKind
    entry: SemanticEntry
    path: tuple[str, ...]
    layout: SpaceLayoutEntry | None = None

    def identity_dict(self) -> dict[str, Any]:
        return {
            "semantic_id": self.semantic_id,
            "source_registry": self.source_registry.value,
            "address": self.entry.address.to_dict(),
            "path": list(self.path),
            "layout": None if self.layout is None else self.layout.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class ActionChannelAudit:
    semantic_id: str
    native_entity: str | None
    status: ActionApplicationStatus
    requested_value: Any = None
    applied_value: Any = None
    realized_value: Any = None
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "semantic_id": self.semantic_id,
            "native_entity": self.native_entity,
            "status": self.status.value,
            "requested_value": self.requested_value,
            "applied_value": self.applied_value,
            "realized_value": self.realized_value,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class HookBinding:
    name: str
    spec: HookSpec
    identity: str
    fn: Callable[..., Any] = field(repr=False, compare=False)
    config: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)

    def identity_dict(self) -> dict[str, Any]:
        return {"name": self.name, "identity": self.identity, "spec": self.spec.to_dict()}


@dataclass(frozen=True, slots=True)
class ProblemRuntimeBinding:
    resolved_problem: ResolvedProblemSpec
    spaces: CompiledGymSpaces
    observation_bindings: tuple[RuntimeChannelBinding, ...]
    action_bindings: tuple[RuntimeChannelBinding, ...]
    disturbance_bindings: tuple[RuntimeChannelBinding, ...]
    parameter_bindings: tuple[RuntimeChannelBinding, ...]
    constraint_bindings: tuple[RuntimeChannelBinding, ...]
    fault_targets: tuple[str, ...]
    disabled_native_controls: tuple[str, ...]
    reward_hook: HookBinding
    termination_hook: HookBinding
    truncation_hook: HookBinding
    implementation_source_sha256: str
    runtime_binding_sha256: str


@dataclass(frozen=True, slots=True)
class RuntimeStepContext:
    step_index: int
    observation: Mapping[str, Any]
    requested_action: Mapping[str, Any]
    applied_action: Mapping[str, Any]
    realized_action: Mapping[str, Any]
    action_audit: tuple[ActionChannelAudit, ...]
    internal_state: Mapping[str, Any]
    disturbances: Mapping[str, Any]
    parameters: Mapping[str, Any]
    constraints: Mapping[str, Any]
    availability: Mapping[str, Any]
    authority: Mapping[str, Any]
    solution: Mapping[str, Any]
    previous_observation: Mapping[str, Any] | None = None

    @classmethod
    def create(cls, **kwargs: Any) -> "RuntimeStepContext":
        previous = kwargs.pop("previous_observation", None)
        for key in (
            "observation", "requested_action", "applied_action", "realized_action",
            "internal_state", "disturbances", "parameters", "constraints",
            "availability", "authority", "solution",
        ):
            kwargs[key] = _readonly_mapping(kwargs.get(key))
        kwargs["previous_observation"] = None if previous is None else _readonly_mapping(previous)
        return cls(**kwargs)
