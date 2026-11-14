"""Strict one-time A04 ProblemSpec resolution against frozen A03 semantics."""

from __future__ import annotations

import math
from typing import Iterable

from opendsssim.persistence.inventory_schema import CircuitInventory
from opendsssim.problem.schema import (
    ActionRestriction,
    ActionSpec,
    CapabilityRequirement,
    ControlAuthorityMode,
    ControlAuthoritySpec,
    DeviceQuery,
    DeviceRef,
    ExactSemanticRef,
    ObservationSpec,
    ProblemSpec,
    RegistryKind,
    RegistrySelectionSpec,
    ResolvedActionSpec,
    ResolvedChannel,
    ResolvedControlAuthoritySpec,
    ResolvedFaultSpec,
    ResolvedObservationSpec,
    ResolvedProblemSpec,
    ResolvedRegistrySelectionSpec,
    ResolvedSelectionGroup,
    SelectionGroup,
    SemanticActionKind,
    SemanticQuery,
)
from opendsssim.semantics.schema import (
    NativePropertyAddress,
    RuntimeCommandAddress,
    RuntimeReadoutAddress,
    SemanticEntry,
    SemanticRegistryBundle,
)


class ProblemResolutionError(ValueError):
    """Fail-closed A04 resolution error."""


class A05DeferredError(NotImplementedError):
    """Raised when A04 is asked to resolve an A05-owned temporal feature."""


def _registry_ids(bundle: SemanticRegistryBundle, kind: RegistryKind) -> tuple[str, ...]:
    registry = {
        RegistryKind.STATE: bundle.state_registry,
        RegistryKind.ACTION: bundle.action_registry,
        RegistryKind.DISTURBANCE: bundle.disturbance_registry,
        RegistryKind.CONSTRAINT: bundle.constraint_registry,
        RegistryKind.PARAMETER: bundle.parameter_registry,
    }[kind]
    return registry.entry_ids


def _identity(entry: SemanticEntry) -> tuple[str, str]:
    entity = entry.native_entity
    if entity:
        if "." in entity:
            dss_class, object_name = entity.split(".", 1)
            return dss_class, object_name
        return "Native", entity

    address = entry.address
    if isinstance(address, NativePropertyAddress):
        if "." in address.object_full_name:
            return tuple(address.object_full_name.split(".", 1))  # type: ignore[return-value]
        return "Native", address.object_full_name
    if isinstance(address, RuntimeReadoutAddress):
        entity = address.entity
        if entity is None:
            return address.service, "__service__"
        if "." in entity:
            return tuple(entity.split(".", 1))  # type: ignore[return-value]
        return address.service, entity
    if isinstance(address, RuntimeCommandAddress):
        if "." in address.entity:
            return tuple(address.entity.split(".", 1))  # type: ignore[return-value]
        return address.service, address.entity
    raise ProblemResolutionError(f"Unsupported semantic address type: {type(address)!r}")


def _canonical_entry_key(entry: SemanticEntry) -> tuple[object, ...]:
    dss_class, object_name = _identity(entry)
    return (
        dss_class.casefold(),
        object_name.casefold(),
        entry.quantity.casefold(),
        tuple((key.casefold(), value.casefold()) for key, value in entry.selectors),
        entry.semantic_id.casefold(),
    )


def _matches_query(entry: SemanticEntry, query: SemanticQuery) -> bool:
    dss_class, object_name = _identity(entry)
    if query.dss_class is not None and dss_class.casefold() != query.dss_class.casefold():
        return False
    if query.object_name is not None and object_name.casefold() != query.object_name.casefold():
        return False
    if query.native_entity is not None:
        if entry.native_entity is None or entry.native_entity.casefold() != query.native_entity.casefold():
            return False
    if query.quantity is not None and entry.quantity.casefold() != query.quantity.casefold():
        return False
    if query.mutability is not None and entry.mutability is not query.mutability:
        return False
    selector_map = {key.casefold(): value.casefold() for key, value in entry.selectors}
    for key, value in query.selectors:
        if selector_map.get(key.casefold()) != value.casefold():
            return False
    tags = {tag.casefold() for tag in entry.capability_tags}
    if any(tag.casefold() not in tags for tag in query.capability_tags):
        return False
    return True


def _resolve_selection(
    selection: ExactSemanticRef | SemanticQuery,
    *,
    bundle: SemanticRegistryBundle,
    allowed_registries: set[RegistryKind],
    label: str,
) -> list[tuple[RegistryKind, SemanticEntry]]:
    if selection.registry not in allowed_registries:
        raise ProblemResolutionError(
            f"{label} selection uses registry {selection.registry.value!r}, "
            f"allowed={sorted(item.value for item in allowed_registries)}."
        )

    ids = _registry_ids(bundle, selection.registry)
    lookup = bundle.entry_by_id()

    if isinstance(selection, ExactSemanticRef):
        if selection.semantic_id not in set(ids):
            raise ProblemResolutionError(
                f"{label} exact semantic id {selection.semantic_id!r} is not present in "
                f"the {selection.registry.value} registry."
            )
        return [(selection.registry, lookup[selection.semantic_id])]

    matched = [lookup[semantic_id] for semantic_id in ids if _matches_query(lookup[semantic_id], selection)]
    matched.sort(key=_canonical_entry_key)
    selection.cardinality.validate(len(matched), label=f"{label} query")
    return [(selection.registry, entry) for entry in matched]


def _as_float(value: object) -> float | None:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        result = float(value)
        return result if math.isfinite(result) else None
    if isinstance(value, str):
        try:
            result = float(value.strip())
        except ValueError:
            return None
        return result if math.isfinite(result) else None
    return None


def _parameter_values(bundle: SemanticRegistryBundle, entity: str, property_name: str) -> list[float]:
    lookup = bundle.entry_by_id()
    values: list[float] = []
    suffix = "." + property_name.casefold()
    for semantic_id in bundle.parameter_registry.entry_ids:
        entry = lookup[semantic_id]
        if entry.native_entity is None or entry.native_entity.casefold() != entity.casefold():
            continue
        if not entry.quantity.casefold().endswith(suffix):
            continue
        raw = entry.metadata_dict().get("compile_time_value")
        candidates = raw if isinstance(raw, (list, tuple)) else [raw]
        for candidate in candidates:
            value = _as_float(candidate)
            if value is not None:
                values.append(value)
    return values


def _parameter_bound(
    bundle: SemanticRegistryBundle,
    entity: str,
    property_name: str,
    *,
    reducer: str,
) -> float | None:
    values = _parameter_values(bundle, entity, property_name)
    if not values:
        return None
    if reducer == "min":
        return min(values)
    if reducer == "max":
        return max(values)
    if reducer == "absmax":
        return max(abs(value) for value in values)
    raise AssertionError(reducer)


def _intrinsic_action_contract(
    entry: SemanticEntry,
    bundle: SemanticRegistryBundle,
) -> tuple[SemanticActionKind, float | None, float | None, tuple[str | int | float, ...], tuple[int, ...] | None]:
    entity = entry.native_entity
    quantity = entry.quantity.casefold()
    dtype = entry.dtype.casefold()
    metadata = entry.metadata_dict()

    if dtype == "enum":
        allowed = tuple(metadata.get("allowed_states", ()))
        if not allowed:
            raise ProblemResolutionError(f"Enum action {entry.semantic_id} lacks allowed_states metadata.")
        return SemanticActionKind.CATEGORICAL, None, None, allowed, entry.shape

    if dtype in {"bool", "boolean"}:
        return SemanticActionKind.BINARY, 0.0, 1.0, (0, 1), entry.shape

    if dtype in {"integer", "int", "integer_array", "int_array"}:
        return SemanticActionKind.ORDERED_INTEGER, None, None, (), entry.shape or None

    if dtype not in {"float", "float64", "double", "float_array"}:
        raise ProblemResolutionError(
            f"Unsupported action dtype {entry.dtype!r} for {entry.semantic_id}."
        )

    low: float | None = None
    high: float | None = None
    if entity is not None:
        if quantity == "pv_reactive_power_command":
            neg = _parameter_bound(bundle, entity, "kvarMaxAbs", reducer="absmax")
            pos = _parameter_bound(bundle, entity, "kvarMax", reducer="absmax")
            kva = _parameter_bound(bundle, entity, "kVA", reducer="absmax")
            low_mag = neg if neg is not None else (pos if pos is not None else kva)
            high_mag = pos if pos is not None else (neg if neg is not None else kva)
            if low_mag is not None:
                low = -abs(low_mag)
            if high_mag is not None:
                high = abs(high_mag)
        elif quantity == "storage_active_power_command":
            rated = _parameter_bound(bundle, entity, "kWRated", reducer="absmax")
            if rated is not None:
                low, high = -rated, rated
        elif quantity == "storage_reactive_power_command":
            neg = _parameter_bound(bundle, entity, "kvarMaxAbs", reducer="absmax")
            pos = _parameter_bound(bundle, entity, "kvarMax", reducer="absmax")
            kva = _parameter_bound(bundle, entity, "kVA", reducer="absmax")
            low_mag = neg if neg is not None else (pos if pos is not None else kva)
            high_mag = pos if pos is not None else (neg if neg is not None else kva)
            if low_mag is not None:
                low = -abs(low_mag)
            if high_mag is not None:
                high = abs(high_mag)
        elif quantity == "transformer_tap_command":
            low = _parameter_bound(bundle, entity, "MinTap", reducer="min")
            high = _parameter_bound(bundle, entity, "MaxTap", reducer="max")
        elif quantity == "load_service_fraction":
            low, high = 0.0, 1.0

    return SemanticActionKind.CONTINUOUS, low, high, (), entry.shape


def _apply_action_restriction(
    *,
    entry: SemanticEntry,
    bundle: SemanticRegistryBundle,
    restriction: ActionRestriction | None,
) -> tuple[SemanticActionKind, float | None, float | None, tuple[str | int | float, ...], tuple[int, ...] | None]:
    kind, intrinsic_low, intrinsic_high, intrinsic_values, intrinsic_shape = _intrinsic_action_contract(entry, bundle)
    low, high = intrinsic_low, intrinsic_high
    values = intrinsic_values
    shape = intrinsic_shape

    if restriction is not None:
        if restriction.shape is not None:
            if shape is not None and tuple(shape) != tuple(restriction.shape):
                raise ProblemResolutionError(
                    f"Problem action shape {restriction.shape} contradicts intrinsic shape {shape} "
                    f"for {entry.semantic_id}."
                )
            shape = restriction.shape

        if restriction.low is not None:
            if intrinsic_low is not None and restriction.low < intrinsic_low:
                raise ProblemResolutionError(
                    f"Problem lower bound {restriction.low} enlarges intrinsic lower bound "
                    f"{intrinsic_low} for {entry.semantic_id}."
                )
            low = restriction.low
        if restriction.high is not None:
            if intrinsic_high is not None and restriction.high > intrinsic_high:
                raise ProblemResolutionError(
                    f"Problem upper bound {restriction.high} enlarges intrinsic upper bound "
                    f"{intrinsic_high} for {entry.semantic_id}."
                )
            high = restriction.high

        if restriction.allowed_values:
            requested = tuple(restriction.allowed_values)
            if intrinsic_values:
                allowed = set(intrinsic_values)
                if any(value not in allowed for value in requested):
                    raise ProblemResolutionError(
                        f"Problem allowed_values enlarge intrinsic domain for {entry.semantic_id}."
                    )
            values = requested

    if kind is SemanticActionKind.CONTINUOUS and (low is None or high is None):
        raise ProblemResolutionError(
            f"Continuous action {entry.semantic_id} lacks deterministic static outer bounds."
        )
    if kind is SemanticActionKind.ORDERED_INTEGER:
        if shape is None:
            raise ProblemResolutionError(
                f"Ordered-integer action {entry.semantic_id} has unresolved shape."
            )
        if not values and (low is None or high is None):
            raise ProblemResolutionError(
                f"Ordered-integer action {entry.semantic_id} lacks a fixed domain."
            )
    return kind, low, high, values, shape


def _resolved_channel(
    registry: RegistryKind,
    entry: SemanticEntry,
    *,
    bundle: SemanticRegistryBundle,
    restriction: ActionRestriction | None,
) -> ResolvedChannel:
    dss_class, object_name = _identity(entry)
    action_kind = None
    low = None
    high = None
    allowed_values: tuple[str | int | float, ...] = ()
    resolved_shape: tuple[int, ...] | None = entry.shape

    if registry is RegistryKind.ACTION:
        action_kind, low, high, allowed_values, resolved_shape = _apply_action_restriction(
            entry=entry,
            bundle=bundle,
            restriction=restriction,
        )

    return ResolvedChannel(
        semantic_id=entry.semantic_id,
        source_registry=registry,
        native_entity=entry.native_entity,
        dss_class=dss_class,
        object_name=object_name,
        quantity=entry.quantity,
        unit=entry.unit,
        dtype=entry.dtype,
        native_shape=entry.shape,
        selectors=entry.selectors,
        address_kind=entry.address.kind,
        capability_tags=entry.capability_tags,
        action_kind=action_kind,
        static_low=low,
        static_high=high,
        allowed_values=allowed_values,
        resolved_shape=resolved_shape,
    )


def _resolve_groups(
    groups: tuple[SelectionGroup, ...],
    *,
    bundle: SemanticRegistryBundle,
    allowed_registries: set[RegistryKind],
    label: str,
    actions: bool = False,
) -> tuple[ResolvedSelectionGroup, ...]:
    result: list[ResolvedSelectionGroup] = []
    seen_ids: set[str] = set()
    seen_group_ids: set[str] = set()

    for group in groups:
        if group.group_id.casefold() in seen_group_ids:
            raise ProblemResolutionError(f"Duplicate {label} group_id: {group.group_id!r}")
        seen_group_ids.add(group.group_id.casefold())

        if not actions and group.action_restriction is not None:
            raise ProblemResolutionError(
                f"Action restriction is not valid on non-action group {group.group_id!r}."
            )

        selected: list[tuple[RegistryKind, SemanticEntry]] = []
        for selection in group.selections:
            selected.extend(
                _resolve_selection(
                    selection,
                    bundle=bundle,
                    allowed_registries=allowed_registries,
                    label=f"{label}.{group.group_id}",
                )
            )

        group.cardinality.validate(len(selected), label=f"{label}.{group.group_id}")

        channels: list[ResolvedChannel] = []
        for registry, entry in selected:
            if entry.semantic_id in seen_ids:
                raise ProblemResolutionError(
                    f"Duplicate semantic channel {entry.semantic_id} in {label} selection."
                )
            seen_ids.add(entry.semantic_id)
            channels.append(
                _resolved_channel(
                    registry,
                    entry,
                    bundle=bundle,
                    restriction=group.action_restriction if actions else None,
                )
            )

        result.append(
            ResolvedSelectionGroup(
                group_id=group.group_id,
                channels=tuple(channels),
                action_restriction=group.action_restriction if actions else None,
            )
        )

    return tuple(result)


def _resolve_observations(
    spec: ObservationSpec,
    bundle: SemanticRegistryBundle,
) -> ResolvedObservationSpec:
    if spec.forecast_groups:
        raise A05DeferredError(
            "Forecast groups are A05-owned. A04I1 does not freeze forecast/profile shapes."
        )
    groups = _resolve_groups(
        spec.groups,
        bundle=bundle,
        allowed_registries={RegistryKind.STATE, RegistryKind.DISTURBANCE, RegistryKind.PARAMETER},
        label="observations",
    )
    return ResolvedObservationSpec(groups)


def _resolve_action_spec(spec: ActionSpec, bundle: SemanticRegistryBundle) -> ResolvedActionSpec:
    groups = _resolve_groups(
        spec.groups,
        bundle=bundle,
        allowed_registries={RegistryKind.ACTION},
        label="actions",
        actions=True,
    )
    return ResolvedActionSpec(groups)


def _resolve_registry_spec(
    spec: RegistrySelectionSpec,
    bundle: SemanticRegistryBundle,
    registry: RegistryKind,
    label: str,
) -> ResolvedRegistrySelectionSpec:
    groups = _resolve_groups(
        spec.groups,
        bundle=bundle,
        allowed_registries={registry},
        label=label,
    )
    return ResolvedRegistrySelectionSpec(groups)


def _resolve_capabilities(
    requirements: tuple[CapabilityRequirement, ...],
    bundle: SemanticRegistryBundle,
) -> tuple[str, ...]:
    available = set(bundle.capability_registry.capability_ids)
    satisfied: list[str] = []
    seen: set[str] = set()
    for requirement in requirements:
        key = requirement.capability_id.casefold()
        if key in seen:
            raise ProblemResolutionError(
                f"Duplicate capability requirement: {requirement.capability_id}"
            )
        seen.add(key)
        present = requirement.capability_id in available
        if requirement.required and not present:
            raise ProblemResolutionError(
                f"Required capability is absent: {requirement.capability_id}"
            )
        if present:
            satisfied.append(requirement.capability_id)
    return tuple(satisfied)


def _canonical_objects(inventory: CircuitInventory) -> dict[str, str]:
    return {item.full_name.casefold(): item.full_name for item in inventory.objects}


def _resolve_faults(spec: ProblemSpec, inventory: CircuitInventory) -> tuple[ResolvedFaultSpec, ...]:
    canonical = _canonical_objects(inventory)
    objects = tuple(canonical.values())
    result: list[ResolvedFaultSpec] = []
    seen_faults: set[str] = set()

    for fault in spec.faults:
        if fault.fault_id.casefold() in seen_faults:
            raise ProblemResolutionError(f"Duplicate fault_id: {fault.fault_id}")
        seen_faults.add(fault.fault_id.casefold())
        targets: list[str] = []
        for target in fault.targets:
            if isinstance(target, DeviceRef):
                resolved = canonical.get(target.full_name.casefold())
                if resolved is None:
                    raise ProblemResolutionError(
                        f"Fault target does not exist in circuit inventory: {target.full_name}"
                    )
                matches = [resolved]
            elif isinstance(target, DeviceQuery):
                matches = []
                for full_name in objects:
                    if "." in full_name:
                        dss_class, object_name = full_name.split(".", 1)
                    else:
                        dss_class, object_name = "Native", full_name
                    if target.dss_class is not None and dss_class.casefold() != target.dss_class.casefold():
                        continue
                    if target.object_name is not None and object_name.casefold() != target.object_name.casefold():
                        continue
                    matches.append(full_name)
                matches.sort(key=str.casefold)
                target.cardinality.validate(len(matches), label=f"fault.{fault.fault_id} query")
            else:  # pragma: no cover - closed union
                raise ProblemResolutionError(f"Unsupported fault target: {target!r}")

            for full_name in matches:
                if full_name.casefold() in {item.casefold() for item in targets}:
                    raise ProblemResolutionError(
                        f"Duplicate resolved fault target {full_name} in fault {fault.fault_id}."
                    )
                targets.append(full_name)
        result.append(ResolvedFaultSpec(fault.fault_id, tuple(targets)))
    return tuple(result)


def _validate_entity_list(
    entities: Iterable[str],
    inventory: CircuitInventory,
    *,
    label: str,
) -> tuple[str, ...]:
    canonical = _canonical_objects(inventory)
    result: list[str] = []
    seen: set[str] = set()
    for entity in entities:
        resolved = canonical.get(entity.casefold())
        if resolved is None:
            raise ProblemResolutionError(f"Unknown {label} entity: {entity}")
        if resolved.casefold() in seen:
            raise ProblemResolutionError(f"Duplicate {label} entity: {entity}")
        seen.add(resolved.casefold())
        result.append(resolved)
    return tuple(result)


def _resolve_authority(
    spec: ControlAuthoritySpec,
    actions: ResolvedActionSpec,
    inventory: CircuitInventory,
) -> ResolvedControlAuthoritySpec:
    selected_entities = {
        channel.native_entity.casefold(): channel.native_entity
        for group in actions.groups
        for channel in group.channels
        if channel.native_entity is not None
    }
    if any(
        channel.native_entity is None
        for group in actions.groups
        for channel in group.channels
    ):
        raise ProblemResolutionError("Every selected action channel must have a native entity.")

    native = _validate_entity_list(spec.native_entities, inventory, label="native-authority")
    external = _validate_entity_list(spec.external_entities, inventory, label="external-authority")
    native_keys = {item.casefold() for item in native}
    external_keys = {item.casefold() for item in external}
    selected_keys = set(selected_entities)

    if native_keys & external_keys:
        overlap = sorted(native_keys & external_keys)
        raise ProblemResolutionError(f"Authority partitions overlap: {overlap}")

    if spec.mode is ControlAuthorityMode.NATIVE:
        if selected_keys:
            raise ProblemResolutionError(
                "NATIVE authority cannot expose external action channels."
            )
        if external_keys:
            raise ProblemResolutionError("NATIVE authority cannot define external_entities.")
    elif spec.mode is ControlAuthorityMode.EXTERNAL:
        if native_keys:
            raise ProblemResolutionError("EXTERNAL authority cannot define native_entities.")
        if not external:
            external = tuple(selected_entities[key] for key in sorted(selected_keys))
            external_keys = selected_keys
        if external_keys != selected_keys:
            raise ProblemResolutionError(
                "EXTERNAL authority entities must exactly match selected action entities."
            )
    elif spec.mode is ControlAuthorityMode.HYBRID:
        if not native or not external:
            raise ProblemResolutionError(
                "HYBRID authority requires explicit non-empty native and external partitions."
            )
        if external_keys != selected_keys:
            raise ProblemResolutionError(
                "HYBRID external_entities must exactly match selected action entities."
            )
    else:  # pragma: no cover
        raise ProblemResolutionError(f"Unsupported authority mode: {spec.mode}")

    return ResolvedControlAuthoritySpec(spec.mode, native, external)


def _verify_inventory_bundle_identity(
    inventory: CircuitInventory,
    bundle: SemanticRegistryBundle,
) -> None:
    if bundle.source_inventory_semantic_sha256 != inventory.semantic_sha256:
        raise ProblemResolutionError(
            "SemanticRegistryBundle and CircuitInventory identity mismatch."
        )
    if bundle.source_tree_sha256 != inventory.source_tree_sha256:
        raise ProblemResolutionError(
            "SemanticRegistryBundle and CircuitInventory source-tree mismatch."
        )


def resolve_problem(
    problem: ProblemSpec | None,
    bundle: SemanticRegistryBundle,
    inventory: CircuitInventory,
) -> ResolvedProblemSpec | None:
    """Resolve a ProblemSpec exactly once against one A03/circuit authority.

    `problem=None` is deliberately preserved and returns `None`; the legacy
    native-controlled plant path remains valid until A04I3 integrates runtime
    problem binding into OpenDSSSimulator.
    """

    _verify_inventory_bundle_identity(inventory, bundle)
    if problem is None:
        return None

    observations = _resolve_observations(problem.observations, bundle)
    actions = _resolve_action_spec(problem.actions, bundle)
    disturbances = _resolve_registry_spec(
        problem.disturbances,
        bundle,
        RegistryKind.DISTURBANCE,
        "disturbances",
    )
    parameters = _resolve_registry_spec(
        problem.parameters,
        bundle,
        RegistryKind.PARAMETER,
        "parameters",
    )
    constraints = _resolve_registry_spec(
        problem.constraints,
        bundle,
        RegistryKind.CONSTRAINT,
        "constraints",
    )
    capabilities = _resolve_capabilities(problem.capability_requirements, bundle)
    faults = _resolve_faults(problem, inventory)
    authority = _resolve_authority(problem.control_authority, actions, inventory)

    resolved = ResolvedProblemSpec(
        authored_problem_spec_sha256=problem.problem_spec_sha256,
        source_semantic_bundle_sha256=bundle.semantic_sha256,
        source_inventory_semantic_sha256=inventory.semantic_sha256,
        source_tree_sha256=inventory.source_tree_sha256,
        problem_id=problem.problem_id,
        problem_version=problem.problem_version,
        observations=observations,
        actions=actions,
        disturbances=disturbances,
        parameters=parameters,
        constraints=constraints,
        satisfied_capabilities=capabilities,
        control_authority=authority,
        faults=faults,
        reward=problem.reward,
        termination=problem.termination,
        truncation=problem.truncation,
        metadata=problem.metadata,
    )
    # Force deterministic identity evaluation here so malformed payloads fail
    # before a runtime can receive the object.
    _ = resolved.resolved_problem_sha256
    return resolved
