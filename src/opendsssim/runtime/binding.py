"""A04I3 immutable runtime binding for one resolved ProblemSpec."""
from __future__ import annotations

from hashlib import sha256
import importlib
import inspect
import json
from typing import Any

from opendsssim.backends.base import DistributionBackend
from opendsssim.persistence.inventory_schema import CircuitInventory
from opendsssim.problem.schema import HookMode, HookSpec, RegistryKind, ResolvedProblemSpec
from opendsssim.problem.spaces import CompiledGymSpaces
from opendsssim.semantics.schema import SemanticEntry, SemanticRegistryBundle

from .identity import canonical_hash, package_source_sha256
from .schema import HookBinding, ProblemRuntimeBinding, RuntimeChannelBinding


class RuntimeBindingError(RuntimeError):
    """Raised when the frozen problem cannot be bound exactly to runtime access."""


def _entry_map(bundle: SemanticRegistryBundle) -> dict[str, SemanticEntry]:
    return {entry.semantic_id: entry for entry in bundle.semantic_entries}


def _layout_map(spaces: CompiledGymSpaces, *, action: bool) -> dict[str, Any]:
    layout = spaces.action_layout if action else spaces.observation_layout
    return {item.semantic_id: item for item in layout}


def _channel_bindings(groups: Any, registry: RegistryKind, entries: dict[str, SemanticEntry], layouts: dict[str, Any] | None = None) -> tuple[RuntimeChannelBinding, ...]:
    result: list[RuntimeChannelBinding] = []
    for group in groups:
        for channel in group.channels:
            entry = entries.get(channel.semantic_id)
            if entry is None:
                raise RuntimeBindingError(f"Resolved semantic ID is absent from A03 bundle: {channel.semantic_id}")
            layout = None if layouts is None else layouts.get(channel.semantic_id)
            if layouts is not None and layout is None:
                raise RuntimeBindingError(f"Compiled Gym layout is missing semantic ID: {channel.semantic_id}")
            path = () if layout is None else tuple(layout.path)
            result.append(RuntimeChannelBinding(channel.semantic_id, registry, entry, path, layout))
    return tuple(result)


def _has_enabled(inventory: CircuitInventory, full_name: str) -> bool:
    key = full_name.casefold()
    for obj in inventory.objects:
        if obj.full_name.casefold() == key:
            return any(name.casefold() == "enabled" for name in obj.property_names)
    for obj in inventory.native_controls:
        if obj.full_name.casefold() == key:
            return any(name.casefold() == "enabled" for name in obj.property_names)
    return False


def _canonical_name(inventory: CircuitInventory, full_name: str) -> str:
    key = full_name.casefold()
    for obj in inventory.objects:
        if obj.full_name.casefold() == key:
            return obj.full_name
    for obj in inventory.native_controls:
        if obj.full_name.casefold() == key:
            return obj.full_name
    raise RuntimeBindingError(f"Runtime entity is absent from circuit inventory: {full_name}")


def _validated_switch_controller(rel: Any, inventory: CircuitInventory) -> str:
    """Prove A02H1 SWITCHES denotes a suppressible SwtControl for one line.

    Discovery's SWITCHES role is distinct from CONTROLS.  Accept it only
    under these additional, runtime-specific checks; never translate other
    relationships into controller ownership.
    """
    if (rel.source_class.casefold() != "swtcontrol"
            or rel.source_full_name.split(".", 1)[0].casefold() != "swtcontrol"
            or rel.property_name.casefold() != "switchedobj"
            or rel.target_kind.casefold() != "object"
            or rel.resolution.casefold() != "explicit_resolved"
            or rel.target_full_name is None):
        raise RuntimeBindingError(
            f"Unqualified SWITCHES native ownership relation: {rel.source_full_name} -> {rel.target_reference}"
        )
    control = _canonical_name(inventory, rel.source_full_name)
    matches = [item for item in inventory.native_controls
               if item.full_name.casefold() == control.casefold()
               and item.dss_class.casefold() == "swtcontrol"]
    if len(matches) != 1 or not _has_enabled(inventory, control):
        raise RuntimeBindingError(f"SWITCHES native controller is not uniquely suppressible: {control}")
    line = _canonical_name(inventory, rel.target_full_name)
    matches = [element for element in inventory.elements
               if element.full_name.casefold() == line.casefold()
               and element.dss_class.casefold() == "line"]
    if (len(matches) != 1 or rel.terminal is None
            or not isinstance(rel.terminal, int)
            or isinstance(rel.terminal, bool)
            or not (1 <= rel.terminal <= matches[0].num_terminals)):
        raise RuntimeBindingError(f"SWITCHES relation has invalid line target/terminal: {control} -> {line}")
    return control


def _native_controls_to_disable(problem: ResolvedProblemSpec, inventory: CircuitInventory) -> tuple[str, ...]:
    external = {item.casefold() for item in problem.control_authority.external_entities}
    native = {item.casefold() for item in problem.control_authority.native_entities}
    external_sources: dict[str, str] = {}
    native_sources: set[str] = set()

    for rel in inventory.control_relationships:
        source = rel.source_full_name.casefold()
        role = rel.role.casefold()
        target = None if rel.target_full_name is None else rel.target_full_name.casefold()
        if role == "switches":
            # An unresolved SwtControl could operate any externally owned line;
            # no exclusivity proof is available, so reject before ANY writes.
            if target is None:
                if rel.source_class.casefold() == "swtcontrol" and any(
                    item.startswith("line.") for item in external
                ):
                    raise RuntimeBindingError(
                        f"Unresolved SWITCHES controller target prevents external line authority: {rel.source_full_name}"
                    )
                continue
            if target in external:
                control = _validated_switch_controller(rel, inventory)
                external_sources[control.casefold()] = control
            if target in native:
                native_sources.add(source)
            continue
        if role != "controls" or target is None:
            # MONITORS and PROTECTS never imply suppression authority.
            continue
        if target in external:
            external_sources[source] = rel.source_full_name
        if target in native:
            native_sources.add(source)

    conflict = set(external_sources) & native_sources
    if conflict:
        names = [external_sources[key] for key in sorted(conflict)]
        raise RuntimeBindingError(
            "A native controller spans both HYBRID native and external actuator partitions: " + ", ".join(names)
        )
    controls = tuple(sorted((_canonical_name(inventory, value) for value in external_sources.values()), key=str.casefold))
    for control in controls:
        if not _has_enabled(inventory, control):
            raise RuntimeBindingError(f"External authority cannot suppress native controller without Enabled property: {control}")
    return controls


def _resolve_fault_targets(problem: ResolvedProblemSpec, inventory: CircuitInventory) -> tuple[str, ...]:
    targets = sorted({name for fault in problem.faults for name in fault.target_full_names}, key=str.casefold)
    for target in targets:
        if not _has_enabled(inventory, target):
            raise RuntimeBindingError(f"Fault target lacks qualified Enabled property: {target}")
    return tuple(targets)


def _source_hash(fn: Any) -> str | None:
    try:
        text = inspect.getsource(fn)
    except (OSError, TypeError):
        return None
    return sha256(text.encode("utf-8")).hexdigest().upper()


def _bind_hook(name: str, spec: HookSpec, default: Any) -> HookBinding:
    if spec.mode is HookMode.DEFAULT:
        return HookBinding(name=name, spec=spec, identity=f"DEFAULT:{name}", fn=default, config={})
    try:
        module = importlib.import_module(str(spec.module))
        obj: Any = module
        for part in str(spec.qualname).split("."):
            obj = getattr(obj, part)
    except Exception as exc:
        raise RuntimeBindingError(f"Unable to import {name} hook {spec.module}:{spec.qualname}") from exc
    if not callable(obj):
        raise RuntimeBindingError(f"Imported {name} hook is not callable: {spec.module}:{spec.qualname}")
    actual_hash = _source_hash(obj)
    if spec.source_sha256 is not None:
        if actual_hash is None or actual_hash.casefold() != spec.source_sha256.casefold():
            raise RuntimeBindingError(f"{name} hook source_sha256 mismatch for {spec.module}:{spec.qualname}")
    config = {key: json.loads(value) for key, value in spec.config}
    identity_payload = {
        "module": spec.module, "qualname": spec.qualname,
        "source_sha256": actual_hash or spec.source_sha256,
        "config": config,
    }
    return HookBinding(name=name, spec=spec, identity=canonical_hash(identity_payload), fn=obj, config=config)


def _default_reward(context: Any, **config: Any) -> float:
    return 0.0


def _default_false(context: Any, **config: Any) -> bool:
    return False


def build_runtime_binding(
    problem: ResolvedProblemSpec,
    spaces: CompiledGymSpaces,
    bundle: SemanticRegistryBundle,
    inventory: CircuitInventory,
    backend: DistributionBackend,
) -> ProblemRuntimeBinding:
    if problem.source_semantic_bundle_sha256 != bundle.semantic_sha256:
        raise RuntimeBindingError("ResolvedProblemSpec semantic-bundle identity mismatch.")
    if problem.source_inventory_semantic_sha256 != inventory.semantic_sha256:
        raise RuntimeBindingError("ResolvedProblemSpec inventory identity mismatch.")
    if problem.resolved_problem_sha256 != spaces.resolved_problem_sha256:
        raise RuntimeBindingError("ResolvedProblemSpec and compiled Gym-space identity mismatch.")

    entries = _entry_map(bundle)
    obs = _channel_bindings(problem.observations.groups, RegistryKind.STATE, entries, _layout_map(spaces, action=False))
    # Observation groups may contain state/disturbance/parameter entries. Preserve true source registry.
    obs = tuple(RuntimeChannelBinding(b.semantic_id, next(
        ch.source_registry for g in problem.observations.groups for ch in g.channels if ch.semantic_id == b.semantic_id
    ), b.entry, b.path, b.layout) for b in obs)
    actions = _channel_bindings(problem.actions.groups, RegistryKind.ACTION, entries, _layout_map(spaces, action=True))
    disturbances = _channel_bindings(problem.disturbances.groups, RegistryKind.DISTURBANCE, entries)
    parameters = _channel_bindings(problem.parameters.groups, RegistryKind.PARAMETER, entries)
    constraints = _channel_bindings(problem.constraints.groups, RegistryKind.CONSTRAINT, entries)

    disabled_controls = _native_controls_to_disable(problem, inventory)
    fault_targets = _resolve_fault_targets(problem, inventory)
    reward = _bind_hook("reward", problem.reward, _default_reward)
    termination = _bind_hook("termination", problem.termination, _default_false)
    truncation = _bind_hook("truncation", problem.truncation, _default_false)
    impl_hash = package_source_sha256()

    identity_payload = {
        "resolved_problem_sha256": problem.resolved_problem_sha256,
        "observation_space_sha256": spaces.observation_space_sha256,
        "action_space_sha256": spaces.action_space_sha256,
        "gym_space_contract_sha256": spaces.gym_space_contract_sha256,
        "inventory_semantic_sha256": inventory.semantic_sha256,
        "semantic_bundle_sha256": bundle.semantic_sha256,
        "backend": inventory.backend,
        "altdss_version": inventory.altdss_version,
        "engine_version": inventory.engine_version,
        "observation_bindings": [item.identity_dict() for item in obs],
        "action_bindings": [item.identity_dict() for item in actions],
        "disturbance_bindings": [item.identity_dict() for item in disturbances],
        "parameter_bindings": [item.identity_dict() for item in parameters],
        "constraint_bindings": [item.identity_dict() for item in constraints],
        "disabled_native_controls": list(disabled_controls),
        "fault_targets": list(fault_targets),
        "hooks": [reward.identity_dict(), termination.identity_dict(), truncation.identity_dict()],
        "implementation_source_sha256": impl_hash,
        "backend_context_type": type(backend).__name__,
    }
    binding_hash = canonical_hash(identity_payload)
    return ProblemRuntimeBinding(
        resolved_problem=problem,
        spaces=spaces,
        observation_bindings=obs,
        action_bindings=actions,
        disturbance_bindings=disturbances,
        parameter_bindings=parameters,
        constraint_bindings=constraints,
        fault_targets=fault_targets,
        disabled_native_controls=disabled_controls,
        reward_hook=reward,
        termination_hook=termination,
        truncation_hook=truncation,
        implementation_source_sha256=impl_hash,
        runtime_binding_sha256=binding_hash,
    )
