"""A03 semantic compiler: CircuitInventory -> SemanticRegistryBundle."""

from __future__ import annotations

from collections import defaultdict
import json
from typing import Any, Iterable

from opendsssim.backends.base import DistributionBackend
from opendsssim.persistence.inventory_schema import (
    CircuitInventory,
    InventoryElement,
    InventoryObject,
)
from opendsssim.semantics.policy import (
    CONSTRAINT_PARAMETER_PROPERTIES,
    NATIVE_CONTROL_CAPABILITY,
    SEMANTIC_POLICY_SHA256,
    STATIC_PARAMETER_PROPERTIES,
)
from opendsssim.semantics.schema import (
    ActionRegistry,
    CapabilityRecord,
    CapabilityRegistry,
    CircuitClassRecord,
    CircuitRegistry,
    CircuitRelationshipRecord,
    ConstraintRegistry,
    DisturbanceRegistry,
    Mutability,
    NativePropertyAddress,
    ParameterRegistry,
    RuntimeCommandAddress,
    RuntimeReadoutAddress,
    SEMANTIC_POLICY_VERSION,
    SEMANTIC_REGISTRY_SCHEMA_VERSION,
    SemanticAddress,
    SemanticEntry,
    SemanticRegistryBundle,
    StateRegistry,
    canonical_json,
    deterministic_semantic_id,
)


def _casefold_map(values: Iterable[str]) -> dict[str, str]:
    return {str(value).casefold(): str(value) for value in values}


def _metadata_pairs(metadata: dict[str, Any] | None) -> tuple[tuple[str, str], ...]:
    if not metadata:
        return ()
    return tuple(
        (str(key), canonical_json(value))
        for key, value in sorted(metadata.items(), key=lambda item: str(item[0]).casefold())
    )


class _BundleBuilder:
    def __init__(self) -> None:
        self.entries: dict[str, SemanticEntry] = {}
        self.views: dict[str, set[str]] = {
            "state": set(),
            "action": set(),
            "disturbance": set(),
            "constraint": set(),
            "parameter": set(),
        }
        self.capability_entries: dict[str, set[str]] = defaultdict(set)
        self.capability_entities: dict[str, set[str]] = defaultdict(set)

    def add(
        self,
        *,
        address: SemanticAddress,
        native_entity: str | None,
        quantity: str,
        mutability: Mutability,
        registries: tuple[str, ...],
        unit: str | None = None,
        dtype: str = "float",
        shape: tuple[int, ...] = (),
        selectors: tuple[tuple[str, str], ...] = (),
        metadata: dict[str, Any] | None = None,
        capabilities: tuple[str, ...] = (),
    ) -> str:
        semantic_id = deterministic_semantic_id(address, quantity, selectors)
        entry = SemanticEntry(
            semantic_id=semantic_id,
            address=address,
            native_entity=native_entity,
            quantity=str(quantity),
            unit=unit,
            dtype=str(dtype),
            shape=tuple(int(value) for value in shape),
            selectors=tuple((str(k), str(v)) for k, v in selectors),
            mutability=mutability,
            static_metadata=_metadata_pairs(metadata),
            capability_tags=tuple(
                sorted(set(capabilities), key=str.casefold)
            ),
        )

        existing = self.entries.get(semantic_id)
        if existing is not None and existing != entry:
            raise ValueError(
                f"Semantic ID collision with unequal entries: {semantic_id}"
            )
        self.entries[semantic_id] = entry

        for registry in registries:
            if registry not in self.views:
                raise ValueError(f"Unknown semantic registry view: {registry}")
            self.views[registry].add(semantic_id)

        for capability in capabilities:
            self.capability_entries[capability].add(semantic_id)
            if native_entity is not None:
                self.capability_entities[capability].add(native_entity)

        return semantic_id

    def add_capability_entity(
        self,
        capability: str,
        native_entity: str,
    ) -> None:
        self.capability_entities[capability].add(native_entity)

    def capability_registry(self) -> CapabilityRegistry:
        capability_ids = sorted(
            set(self.capability_entries) | set(self.capability_entities),
            key=str.casefold,
        )
        return CapabilityRegistry(
            capabilities=tuple(
                CapabilityRecord(
                    capability_id=capability,
                    evidence_entry_ids=tuple(
                        sorted(
                            self.capability_entries.get(capability, ()),
                            key=str.casefold,
                        )
                    ),
                    evidence_native_entities=tuple(
                        sorted(
                            self.capability_entities.get(capability, ()),
                            key=str.casefold,
                        )
                    ),
                )
                for capability in capability_ids
            )
        )


def _read_static_metadata(
    backend: DistributionBackend,
    obj: InventoryObject,
) -> dict[str, Any]:
    requested = STATIC_PARAMETER_PROPERTIES.get(obj.dss_class, ())
    if not requested:
        return {}

    available = _casefold_map(obj.property_names)
    actual_names = tuple(
        available[name.casefold()]
        for name in requested
        if name.casefold() in available
    )
    if not actual_names:
        return {}

    return backend.read_object_properties(obj.full_name, actual_names)


def _element_by_name(
    inventory: CircuitInventory,
) -> dict[str, InventoryElement]:
    return {item.full_name.casefold(): item for item in inventory.elements}


def _static_truth(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().casefold() in {"yes", "true", "1", "on", "closed"}
    return False


def _controlled_targets(
    inventory: CircuitInventory,
    *,
    source_class: str | None = None,
    role: str | None = None,
) -> set[str]:
    result: set[str] = set()
    for relationship in inventory.control_relationships:
        if source_class is not None and relationship.source_class != source_class:
            continue
        if role is not None and relationship.role != role:
            continue
        if relationship.target_full_name:
            result.add(relationship.target_full_name.casefold())
    return result


def _add_generic_runtime_states(
    builder: _BundleBuilder,
    inventory: CircuitInventory,
) -> None:
    for bus in sorted(inventory.buses, key=lambda item: item.name.casefold()):
        for channel, quantity, unit in (
            ("voltage", "bus_voltage", "V"),
            ("pu_voltage", "bus_voltage_pu", "pu"),
        ):
            builder.add(
                address=RuntimeReadoutAddress(
                    service="Bus",
                    entity=bus.name,
                    channel=channel,
                ),
                native_entity=f"Bus.{bus.name}",
                quantity=quantity,
                mutability=Mutability.READ_ONLY,
                registries=("state",),
                unit=unit,
                dtype="complex" if channel == "voltage" else "float",
                shape=(len(bus.node_names),),
                capabilities=("observation.bus_voltage",),
            )

    for element in sorted(
        inventory.elements,
        key=lambda item: item.full_name.casefold(),
    ):
        builder.add(
            address=RuntimeReadoutAddress(
                service="CircuitElement",
                entity=element.full_name,
                channel="currents",
            ),
            native_entity=element.full_name,
            quantity="element_current",
            mutability=Mutability.READ_ONLY,
            registries=("state",),
            unit="A",
            dtype="complex",
            capabilities=("observation.element_current",),
        )
        builder.add(
            address=RuntimeReadoutAddress(
                service="CircuitElement",
                entity=element.full_name,
                channel="terminal_power",
            ),
            native_entity=element.full_name,
            quantity="element_terminal_power",
            mutability=Mutability.READ_ONLY,
            registries=("state",),
            unit="kVA",
            dtype="complex",
            capabilities=("observation.element_power",),
        )
        builder.add(
            address=RuntimeReadoutAddress(
                service="CircuitElement",
                entity=element.full_name,
                channel="losses",
            ),
            native_entity=element.full_name,
            quantity="element_losses",
            mutability=Mutability.READ_ONLY,
            registries=("state",),
            unit="W+jvar",
            dtype="complex",
            capabilities=("observation.element_losses",),
        )

    builder.add(
        address=RuntimeReadoutAddress(
            service="Solution",
            entity=None,
            channel="converged",
        ),
        native_entity=None,
        quantity="solution_converged",
        mutability=Mutability.READ_ONLY,
        registries=("state",),
        dtype="bool",
        capabilities=("service.snapshot_solve",),
    )
    builder.add(
        address=RuntimeReadoutAddress(
            service="Topology",
            entity=None,
            channel="connectivity",
        ),
        native_entity=None,
        quantity="topology_connectivity",
        mutability=Mutability.READ_ONLY,
        registries=("state",),
        dtype="object",
        capabilities=("service.topology", "observation.connectivity"),
    )


def _add_parameter_entries(
    builder: _BundleBuilder,
    obj: InventoryObject,
    static_metadata: dict[str, Any],
) -> dict[str, str]:
    ids: dict[str, str] = {}
    constraint_names = {
        name.casefold()
        for name in CONSTRAINT_PARAMETER_PROPERTIES.get(obj.dss_class, ())
    }

    for property_name, value in sorted(
        static_metadata.items(),
        key=lambda item: str(item[0]).casefold(),
    ):
        registries = ["parameter"]
        capabilities: list[str] = []

        if property_name.casefold() in constraint_names:
            registries.append("constraint")

            if obj.dss_class in {"Line"} and property_name.casefold() in {
                "normamps",
                "emergamps",
            }:
                capabilities.append("constraint.ampacity")
            elif obj.dss_class in {"Transformer", "AutoTrans"}:
                capabilities.append("constraint.tap_bounds")
            elif obj.dss_class == "PVSystem":
                capabilities.append("constraint.inverter_capability")
            elif obj.dss_class == "Storage":
                capabilities.append("constraint.storage_capability")
            elif obj.dss_class == "Generator":
                capabilities.append("constraint.generator_capability")

        semantic_id = builder.add(
            address=NativePropertyAddress(
                object_full_name=obj.full_name,
                property_name=property_name,
            ),
            native_entity=obj.full_name,
            quantity=f"{obj.dss_class}.{property_name}",
            mutability=Mutability.INIT_ONLY,
            registries=tuple(registries),
            dtype=type(value).__name__,
            metadata={"compile_time_value": value},
            capabilities=tuple(capabilities),
        )
        ids[property_name.casefold()] = semantic_id

    return ids


def _fixed_array_shape(value: Any, *, label: str) -> tuple[int, ...]:
    """A03/S06 general fixed-shape discovery from a genuine native readback.

    The shape is not inferred from the number of devices, the feeder name,
    or an assumed one-step capacitor/two-winding transformer convention.
    """
    if not isinstance(value, (tuple, list)) or not value:
        raise ValueError(f"S06_FIXED_ARRAY_SHAPE_UNAVAILABLE: {label}")
    return (len(value),)


def _native_array_shape(backend: DistributionBackend, full: str, prop: str) -> tuple[int, ...]:
    raw = backend.read_object_properties(full, (prop,))
    matches = [value for key, value in raw.items() if key.casefold() == prop.casefold()]
    if len(matches) != 1:
        raise ValueError(f"S06_NATIVE_ARRAY_READBACK_MISSING: {full}.{prop}")
    return _fixed_array_shape(matches[0], label=f"{full}.{prop}")


def _runtime_array_shape(backend: DistributionBackend, service: str, entity: str, channel: str) -> tuple[int, ...]:
    return _fixed_array_shape(backend.read_runtime_channel(service, entity, channel),
                              label=f"{service}.{entity}.{channel}")


def _element_terminal_shape(element: InventoryElement | None, full: str) -> tuple[int, ...]:
    if element is None or isinstance(element.num_terminals, bool) or int(element.num_terminals) < 1:
        raise ValueError(f"S06_SWITCH_TERMINAL_CARDINALITY_UNAVAILABLE: {full}")
    return (int(element.num_terminals),)


def _add_class_semantics(
    builder: _BundleBuilder,
    backend: DistributionBackend,
    inventory: CircuitInventory,
    obj: InventoryObject,
    static_metadata: dict[str, Any],
    parameter_ids: dict[str, str],
    element_lookup: dict[str, InventoryElement],
    reg_targets: set[str],
    switch_targets: set[str],
) -> None:
    props = _casefold_map(obj.property_names)
    cls = obj.dss_class
    full = obj.full_name
    element = element_lookup.get(full.casefold())

    if cls == "Load":
        for prop, quantity, unit in (
            ("kW", "load_active_power_demand", "kW"),
            ("kvar", "load_reactive_power_demand", "kvar"),
        ):
            actual = props.get(prop.casefold())
            if actual:
                builder.add(
                    address=NativePropertyAddress(full, actual),
                    native_entity=full,
                    quantity=quantity,
                    mutability=Mutability.STEP_EXOGENOUS,
                    registries=("disturbance",),
                    unit=unit,
                    capabilities=("disturbance.load_power",),
                )
        # S06: a separate service command, never dual ownership of Load.kW/kvar.
        # Native A05 writes update uncurtailed demand; the service action scales
        # both P and Q together after that physical demand is applied.
        if "kw" in props and "kvar" in props:
            builder.add(
                address=RuntimeCommandAddress(service="Load", entity=full,
                                              operation="set_served_fraction"),
                native_entity=full,
                quantity="load_service_fraction",
                mutability=Mutability.STEP_CONTROLLABLE,
                registries=("action",),
                unit="fraction", dtype="float",
                metadata={"minimum": 0.0, "maximum": 1.0},
                capabilities=("control.load_service_fraction",),
            )
            for channel, quantity, unit in (
                ("applied_fraction", "load_service_applied_fraction", "fraction"),
                ("demand_base_kw", "load_available_active_demand_kw", "kW"),
                ("demand_base_kvar", "load_available_reactive_demand_kvar", "kvar"),
            ):
                builder.add(
                    address=RuntimeReadoutAddress(service="Load", entity=full, channel=channel),
                    native_entity=full,
                    quantity=quantity, mutability=Mutability.READ_ONLY,
                    registries=("state",), unit=unit, dtype="float",
                    capabilities=("observation.load_service",),
                )
        return

    if cls == "PVSystem":
        actual_q = props.get("kvar")
        if actual_q:
            builder.add(
                address=NativePropertyAddress(full, actual_q),
                native_entity=full,
                quantity="pv_reactive_power_command",
                mutability=Mutability.STEP_CONTROLLABLE,
                registries=("action",),
                unit="kvar",
                capabilities=("control.pv_reactive_power",),
            )

        for candidate in ("Irradiance", "pctPmpp"):
            actual = props.get(candidate.casefold())
            if actual:
                builder.add(
                    address=NativePropertyAddress(full, actual),
                    native_entity=full,
                    quantity="pv_active_power_availability_driver",
                    mutability=Mutability.STEP_EXOGENOUS,
                    registries=("disturbance",),
                    dtype="float",
                    capabilities=("disturbance.pv_availability",),
                )
                break
        return

    if cls == "Storage":
        for prop, quantity, unit, capability in (
            ("kW", "storage_active_power_command", "kW", "control.storage_active_power"),
            ("kvar", "storage_reactive_power_command", "kvar", "control.storage_reactive_power"),
        ):
            actual = props.get(prop.casefold())
            if actual:
                builder.add(
                    address=NativePropertyAddress(full, actual),
                    native_entity=full,
                    quantity=quantity,
                    mutability=Mutability.STEP_CONTROLLABLE,
                    registries=("action",),
                    unit=unit,
                    capabilities=(capability,),
                )

        actual_soc = props.get("pctstored")
        if actual_soc:
            builder.add(
                address=NativePropertyAddress(full, actual_soc),
                native_entity=full,
                quantity="storage_state_of_charge",
                mutability=Mutability.READ_ONLY,
                registries=("state",),
                unit="percent",
                capabilities=("observation.storage_soc",),
            )
        return

    if cls == "Capacitor":
        actual = props.get("states")
        if actual:
            builder.add(
                address=NativePropertyAddress(full, actual),
                native_entity=full,
                quantity="capacitor_state",
                mutability=Mutability.STEP_CONTROLLABLE,
                registries=("state", "action", "constraint"),
                dtype="integer_array",
                shape=_native_array_shape(backend, full, actual),
                capabilities=(
                    "observation.capacitor_state",
                    "control.capacitor_switching",
                    "constraint.capacitor_state_domain",
                ),
            )
        return

    if cls in {"Transformer", "AutoTrans"}:
        builder.add(
            address=RuntimeReadoutAddress(
                service=cls,
                entity=full,
                channel="taps",
            ),
            native_entity=full,
            quantity="transformer_tap_position",
            mutability=Mutability.READ_ONLY,
            registries=("state",),
            dtype="float_array",
            shape=_runtime_array_shape(backend, cls, full, "taps"),
            capabilities=("observation.regulator_tap",),
        )

        controllable = (
            full.casefold() in reg_targets
            or bool(element and element.has_volt_control)
        )
        if controllable:
            builder.add(
                address=RuntimeCommandAddress(
                    service=cls,
                    entity=full,
                    operation="set_tap",
                ),
                native_entity=full,
                quantity="transformer_tap_command",
                mutability=Mutability.STEP_CONTROLLABLE,
                registries=("action",),
                dtype="float",
                capabilities=("control.regulator_tap",),
            )
        return

    if cls == "Line":
        switchable = (
            full.casefold() in switch_targets
            or bool(element and element.has_switch_control)
            or _static_truth(static_metadata.get("Switch", False))
        )
        if switchable:
            builder.add(
                address=RuntimeReadoutAddress(
                    service="CircuitElement",
                    entity=full,
                    channel="open_state",
                ),
                native_entity=full,
                quantity="branch_open_state",
                mutability=Mutability.READ_ONLY,
                registries=("state",),
                dtype="bool_array",
                # The registered element terminal count is the native
                # IsOpen(terminal, 0) readout cardinality, independent of solve.
                shape=_element_terminal_shape(element, full),
                capabilities=("observation.branch_switch_state",),
            )
            builder.add(
                address=RuntimeCommandAddress(
                    service="CircuitElement",
                    entity=full,
                    operation="open_close",
                ),
                native_entity=full,
                quantity="branch_switch_command",
                mutability=Mutability.STEP_CONTROLLABLE,
                registries=("action", "constraint"),
                dtype="enum",
                metadata={"allowed_states": ["OPEN", "CLOSED"]},
                capabilities=(
                    "control.branch_switching",
                    "constraint.branch_switch_domain",
                ),
            )
        return

    if cls == "Generator":
        # Conservative A03-v1 policy: generator dispatch is not promoted to a
        # step action without a later explicit generator-control policy revision.
        return

    if cls in NATIVE_CONTROL_CAPABILITY:
        builder.add_capability_entity(
            NATIVE_CONTROL_CAPABILITY[cls],
            full,
        )


def _circuit_registry(inventory: CircuitInventory) -> CircuitRegistry:
    return CircuitRegistry(
        circuit_name=inventory.circuit_name,
        bus_names=tuple(
            sorted((item.name for item in inventory.buses), key=str.casefold)
        ),
        node_names=tuple(inventory.node_names),
        classes=tuple(
            CircuitClassRecord(
                dss_class=item.dss_class,
                object_full_names=tuple(item.object_full_names),
            )
            for item in sorted(
                inventory.classes,
                key=lambda item: item.dss_class.casefold(),
            )
        ),
        object_full_names=tuple(
            sorted(
                (item.full_name for item in inventory.objects),
                key=str.casefold,
            )
        ),
        control_relationships=tuple(
            CircuitRelationshipRecord(
                source_full_name=item.source_full_name,
                source_class=item.source_class,
                role=item.role,
                property_name=item.property_name,
                target_reference=item.target_reference,
                target_full_name=item.target_full_name,
                target_kind=item.target_kind,
                resolution=item.resolution,
                terminal=item.terminal,
                winding=item.winding,
                tap_winding=item.tap_winding,
            )
            for item in inventory.control_relationships
        ),
    )


def compile_semantic_registry_bundle(
    inventory: CircuitInventory,
    backend: DistributionBackend,
) -> SemanticRegistryBundle:
    """Compile one deterministic A03 bundle from valid A02H1 inventory.

    This function never invokes A02 circuit discovery. It reads only explicit,
    policy-selected static object properties through the backend read-only API.
    """

    builder = _BundleBuilder()
    _add_generic_runtime_states(builder, inventory)

    element_lookup = _element_by_name(inventory)
    reg_targets = _controlled_targets(
        inventory,
        source_class="RegControl",
        role="CONTROLS",
    )
    switch_targets = _controlled_targets(
        inventory,
        source_class="SwtControl",
        role="SWITCHES",
    )

    for obj in sorted(
        inventory.objects,
        key=lambda item: item.full_name.casefold(),
    ):
        static_metadata = _read_static_metadata(backend, obj)
        parameter_ids = _add_parameter_entries(
            builder,
            obj,
            static_metadata,
        )
        _add_class_semantics(
            builder,
            backend,
            inventory,
            obj,
            static_metadata,
            parameter_ids,
            element_lookup,
            reg_targets,
            switch_targets,
        )

    entries = tuple(
        builder.entries[key]
        for key in sorted(builder.entries, key=str.casefold)
    )

    return SemanticRegistryBundle(
        registry_schema_version=SEMANTIC_REGISTRY_SCHEMA_VERSION,
        semantic_policy_version=SEMANTIC_POLICY_VERSION,
        semantic_policy_sha256=SEMANTIC_POLICY_SHA256,
        source_inventory_semantic_sha256=inventory.semantic_sha256,
        source_tree_sha256=inventory.source_tree_sha256,
        backend=inventory.backend,
        altdss_version=inventory.altdss_version,
        engine_version=inventory.engine_version,
        semantic_entries=entries,
        circuit_registry=_circuit_registry(inventory),
        state_registry=StateRegistry(
            entry_ids=tuple(sorted(builder.views["state"], key=str.casefold))
        ),
        action_registry=ActionRegistry(
            entry_ids=tuple(sorted(builder.views["action"], key=str.casefold))
        ),
        disturbance_registry=DisturbanceRegistry(
            entry_ids=tuple(
                sorted(builder.views["disturbance"], key=str.casefold)
            )
        ),
        constraint_registry=ConstraintRegistry(
            entry_ids=tuple(
                sorted(builder.views["constraint"], key=str.casefold)
            )
        ),
        parameter_registry=ParameterRegistry(
            entry_ids=tuple(
                sorted(builder.views["parameter"], key=str.casefold)
            )
        ),
        capability_registry=builder.capability_registry(),
    )
