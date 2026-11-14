"""A04 compilation of resolved semantic channels to canonical Gymnasium spaces."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from hashlib import sha256
import math
from typing import Any

import gymnasium as gym
from gymnasium import spaces
import numpy as np

from opendsssim.problem.schema import (
    GYM_SPACE_SCHEMA_VERSION,
    RegistryKind,
    ResolvedChannel,
    ResolvedProblemSpec,
    SemanticActionKind,
)
from opendsssim.semantics.schema import canonical_json


class GymSpaceCompilationError(ValueError):
    """Fail-closed semantic-to-Gym compilation error."""


def _number_token(value: float) -> float | str:
    if math.isinf(value):
        return "Infinity" if value > 0 else "-Infinity"
    if math.isnan(value):
        raise GymSpaceCompilationError("NaN is not valid space provenance.")
    return float(value)


@dataclass(frozen=True)
class SpaceLayoutEntry:
    path: tuple[str, ...]
    semantic_id: str
    source_registry: str
    space_type: str
    shape: tuple[int, ...]
    dtype: str
    selector_order: tuple[tuple[str, str], ...]
    component_order: tuple[str, ...] = ()
    low: float | None = None
    high: float | None = None
    domain_values: tuple[str | int | float, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": list(self.path),
            "semantic_id": self.semantic_id,
            "source_registry": self.source_registry,
            "space_type": self.space_type,
            "shape": list(self.shape),
            "dtype": self.dtype,
            "selector_order": [[key, value] for key, value in self.selector_order],
            "component_order": list(self.component_order),
            "low": self.low,
            "high": self.high,
            "domain_values": list(self.domain_values),
        }


@dataclass(frozen=True)
class CompiledGymSpaces:
    observation_space: gym.Space[Any]
    action_space: gym.Space[Any]
    observation_layout: tuple[SpaceLayoutEntry, ...]
    action_layout: tuple[SpaceLayoutEntry, ...]
    problem_mode: str
    resolved_problem_sha256: str | None
    schema_version: str = GYM_SPACE_SCHEMA_VERSION

    def _layout_payload(self, which: str) -> dict[str, Any]:
        layout = self.observation_layout if which == "observation" else self.action_layout
        return {
            "schema_version": self.schema_version,
            "problem_mode": self.problem_mode,
            "resolved_problem_sha256": self.resolved_problem_sha256,
            "kind": which,
            "layout": [item.to_dict() for item in layout],
        }

    @property
    def observation_space_sha256(self) -> str:
        return sha256(canonical_json(self._layout_payload("observation")).encode("utf-8")).hexdigest().upper()

    @property
    def action_space_sha256(self) -> str:
        return sha256(canonical_json(self._layout_payload("action")).encode("utf-8")).hexdigest().upper()

    @property
    def gym_space_contract_sha256(self) -> str:
        payload = {
            "schema_version": self.schema_version,
            "problem_mode": self.problem_mode,
            "resolved_problem_sha256": self.resolved_problem_sha256,
            "observation_space_sha256": self.observation_space_sha256,
            "action_space_sha256": self.action_space_sha256,
        }
        return sha256(canonical_json(payload).encode("utf-8")).hexdigest().upper()


class _TreeNode(OrderedDict[str, Any]):
    pass


def _insert_leaf(root: _TreeNode, path: tuple[str, ...], leaf: gym.Space[Any]) -> None:
    if not path:
        raise GymSpaceCompilationError("Semantic space path cannot be empty.")
    node: _TreeNode = root
    for key in path[:-1]:
        current = node.get(key)
        if current is None:
            child = _TreeNode()
            node[key] = child
            node = child
        elif isinstance(current, _TreeNode):
            node = current
        else:
            raise GymSpaceCompilationError(
                f"Semantic path collision: {'.'.join(path)} crosses an existing leaf."
            )
    final = path[-1]
    if final in node:
        raise GymSpaceCompilationError(f"Duplicate semantic Gym path: {'.'.join(path)}")
    node[final] = leaf


def _to_dict_space(node: _TreeNode) -> spaces.Dict:
    converted: OrderedDict[str, gym.Space[Any]] = OrderedDict()
    for key, value in node.items():
        converted[key] = _to_dict_space(value) if isinstance(value, _TreeNode) else value
    return spaces.Dict(converted)


def _resolved_numeric_shape(channel: ResolvedChannel) -> tuple[int, ...]:
    shape = channel.resolved_shape if channel.resolved_shape is not None else channel.native_shape
    dtype = channel.dtype.casefold()
    if dtype.endswith("_array") and not shape:
        raise GymSpaceCompilationError(
            f"Array semantic {channel.semantic_id} has unresolved fixed shape."
        )
    if dtype == "complex":
        return tuple(shape) + (2,)
    return tuple(shape)


def _observation_leaf(channel: ResolvedChannel) -> tuple[gym.Space[Any], SpaceLayoutEntry]:
    dtype = channel.dtype.casefold()
    shape = _resolved_numeric_shape(channel)
    component_order: tuple[str, ...] = ()

    if dtype in {"float", "float64", "double", "float_array"}:
        leaf: gym.Space[Any] = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=shape,
            dtype=np.float64,
        )
        space_type = "Box"
        leaf_dtype = "float64"
    elif dtype == "complex":
        leaf = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=shape,
            dtype=np.float64,
        )
        space_type = "Box"
        leaf_dtype = "float64"
        component_order = ("real", "imag")
    elif dtype in {"bool", "boolean"}:
        if shape:
            leaf = spaces.MultiBinary(shape)
            space_type = "MultiBinary"
            leaf_dtype = "int8"
        else:
            leaf = spaces.Discrete(2)
            space_type = "Discrete"
            leaf_dtype = "int64"
    elif dtype == "bool_array":
        if not shape:
            raise GymSpaceCompilationError(
                f"Boolean-array semantic {channel.semantic_id} has unresolved fixed shape."
            )
        leaf = spaces.MultiBinary(shape)
        space_type = "MultiBinary"
        leaf_dtype = "int8"
    elif dtype in {"int", "integer", "int_array", "integer_array"}:
        # A03 does not generally supply a finite observation integer domain.
        # Preserve the values losslessly in a fixed-shape float64 Box until a
        # registered finite discrete domain exists.
        leaf = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=shape,
            dtype=np.float64,
        )
        space_type = "Box"
        leaf_dtype = "float64"
    else:
        raise GymSpaceCompilationError(
            f"Unsupported observation dtype {channel.dtype!r} for {channel.semantic_id}."
        )

    path = ("current", channel.dss_class, channel.object_name, channel.quantity)
    layout = SpaceLayoutEntry(
        path=path,
        semantic_id=channel.semantic_id,
        source_registry=channel.source_registry.value,
        space_type=space_type,
        shape=shape,
        dtype=leaf_dtype,
        selector_order=channel.selectors,
        component_order=component_order,
    )
    return leaf, layout


def _require_int(value: float | None, *, label: str) -> int:
    if value is None or int(value) != value:
        raise GymSpaceCompilationError(f"{label} requires an integer bound, got {value}.")
    return int(value)


def _action_leaf(channel: ResolvedChannel) -> tuple[gym.Space[Any], SpaceLayoutEntry]:
    kind = channel.action_kind
    if kind is None:
        raise GymSpaceCompilationError(f"Action channel {channel.semantic_id} lacks action kind.")
    shape = channel.resolved_shape if channel.resolved_shape is not None else channel.native_shape
    domain = tuple(channel.allowed_values)
    low = channel.static_low
    high = channel.static_high

    if kind is SemanticActionKind.CONTINUOUS:
        if low is None or high is None:
            raise GymSpaceCompilationError(
                f"Continuous action {channel.semantic_id} lacks static bounds."
            )
        leaf: gym.Space[Any] = spaces.Box(
            low=np.full(shape, low, dtype=np.float64) if shape else np.array(low, dtype=np.float64),
            high=np.full(shape, high, dtype=np.float64) if shape else np.array(high, dtype=np.float64),
            shape=tuple(shape),
            dtype=np.float64,
        )
        space_type = "Box"
        leaf_dtype = "float64"
    elif kind is SemanticActionKind.BINARY:
        if shape:
            leaf = spaces.MultiBinary(tuple(shape))
            space_type = "MultiBinary"
            leaf_dtype = "int8"
        else:
            leaf = spaces.Discrete(2)
            space_type = "Discrete"
            leaf_dtype = "int64"
        if not domain:
            domain = (0, 1)
    elif kind is SemanticActionKind.CATEGORICAL:
        if not domain:
            raise GymSpaceCompilationError(
                f"Categorical action {channel.semantic_id} lacks domain values."
            )
        if shape:
            raise GymSpaceCompilationError(
                f"Categorical array action {channel.semantic_id} is not supported in A04I1."
            )
        leaf = spaces.Discrete(len(domain))
        space_type = "Discrete"
        leaf_dtype = "int64"
    elif kind is SemanticActionKind.ORDERED_INTEGER:
        if domain:
            ints = tuple(int(value) for value in domain)
            if any(int(value) != value for value in domain):
                raise GymSpaceCompilationError(
                    f"Ordered integer domain is not integral for {channel.semantic_id}."
                )
            ordered = tuple(sorted(set(ints)))
            if ordered != tuple(range(ordered[0], ordered[-1] + 1)):
                raise GymSpaceCompilationError(
                    f"Ordered integer domain is not contiguous for {channel.semantic_id}."
                )
            start = ordered[0]
            count = len(ordered)
        else:
            start = _require_int(low, label="Ordered integer lower bound")
            upper = _require_int(high, label="Ordered integer upper bound")
            count = upper - start + 1
            if count < 1:
                raise GymSpaceCompilationError(f"Invalid ordered integer range for {channel.semantic_id}.")
            domain = tuple(range(start, upper + 1))
        if shape:
            nvec = np.full(tuple(shape), count, dtype=np.int64)
            starts = np.full(tuple(shape), start, dtype=np.int64)
            leaf = spaces.MultiDiscrete(nvec=nvec, start=starts)
            space_type = "MultiDiscrete"
            leaf_dtype = "int64"
        else:
            leaf = spaces.Discrete(count, start=start)
            space_type = "Discrete"
            leaf_dtype = "int64"
    else:  # pragma: no cover
        raise GymSpaceCompilationError(f"Unsupported action kind: {kind}")

    path = (channel.dss_class, channel.object_name, channel.quantity)
    layout = SpaceLayoutEntry(
        path=path,
        semantic_id=channel.semantic_id,
        source_registry=RegistryKind.ACTION.value,
        space_type=space_type,
        shape=tuple(shape),
        dtype=leaf_dtype,
        selector_order=channel.selectors,
        low=low,
        high=high,
        domain_values=domain,
    )
    return leaf, layout


def _legacy_no_problem_spaces() -> CompiledGymSpaces:
    observation_space = spaces.Dict(
        OrderedDict((("converged", spaces.Discrete(2)),))
    )
    action_space = spaces.Dict(OrderedDict())
    observation_layout = (
        SpaceLayoutEntry(
            path=("converged",),
            semantic_id="legacy:solution_converged",
            source_registry="legacy",
            space_type="Discrete",
            shape=(),
            dtype="int64",
            selector_order=(),
            domain_values=(0, 1),
        ),
    )
    return CompiledGymSpaces(
        observation_space=observation_space,
        action_space=action_space,
        observation_layout=observation_layout,
        action_layout=(),
        problem_mode="NONE",
        resolved_problem_sha256=None,
    )


def compile_gym_spaces(problem: ResolvedProblemSpec | None) -> CompiledGymSpaces:
    """Compile deterministic canonical Gym spaces from resolved semantics only."""

    if problem is None:
        return _legacy_no_problem_spaces()

    observation_tree = _TreeNode()
    observation_layout: list[SpaceLayoutEntry] = []
    for group in problem.observations.groups:
        for channel in group.channels:
            leaf, layout = _observation_leaf(channel)
            _insert_leaf(observation_tree, layout.path, leaf)
            observation_layout.append(layout)

    # Keep the canonical current root even for an explicitly empty observation.
    if "current" not in observation_tree:
        observation_tree["current"] = _TreeNode()

    action_tree = _TreeNode()
    action_layout: list[SpaceLayoutEntry] = []
    for group in problem.actions.groups:
        for channel in group.channels:
            leaf, layout = _action_leaf(channel)
            _insert_leaf(action_tree, layout.path, leaf)
            action_layout.append(layout)

    compiled = CompiledGymSpaces(
        observation_space=_to_dict_space(observation_tree),
        action_space=_to_dict_space(action_tree),
        observation_layout=tuple(observation_layout),
        action_layout=tuple(action_layout),
        problem_mode="RESOLVED",
        resolved_problem_sha256=problem.resolved_problem_sha256,
    )
    _ = compiled.gym_space_contract_sha256
    return compiled
