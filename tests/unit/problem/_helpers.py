from __future__ import annotations

import json

from opendsssim.persistence.inventory_schema import (
    CONTROL_RELATIONSHIP_SCHEMA_VERSION,
    INVENTORY_SCHEMA_VERSION,
    CircuitInventory,
    InventoryBus,
    InventoryClass,
    InventoryObject,
)
from opendsssim.problem.schema import RegistryKind
from opendsssim.semantics.schema import (
    ActionRegistry,
    CapabilityRecord,
    CapabilityRegistry,
    CircuitClassRecord,
    CircuitRegistry,
    ConstraintRegistry,
    DisturbanceRegistry,
    Mutability,
    NativePropertyAddress,
    ParameterRegistry,
    RuntimeCommandAddress,
    RuntimeReadoutAddress,
    SEMANTIC_POLICY_VERSION,
    SEMANTIC_REGISTRY_SCHEMA_VERSION,
    SemanticEntry,
    SemanticRegistryBundle,
    StateRegistry,
    deterministic_semantic_id,
)


def _metadata(**kwargs):
    return tuple(
        (key, json.dumps(value, sort_keys=True, separators=(",", ":")))
        for key, value in sorted(kwargs.items())
    )


def entry(
    address,
    quantity,
    *,
    entity=None,
    dtype="float",
    shape=(),
    unit=None,
    mutability=Mutability.READ_ONLY,
    metadata=None,
    tags=(),
):
    return SemanticEntry(
        semantic_id=deterministic_semantic_id(address, quantity),
        address=address,
        native_entity=entity,
        quantity=quantity,
        unit=unit,
        dtype=dtype,
        shape=tuple(shape),
        selectors=(),
        mutability=mutability,
        static_metadata=_metadata(**(metadata or {})),
        capability_tags=tuple(tags),
    )


def make_inventory_and_bundle():
    objects = (
        InventoryObject("PVSystem.PV1", "PVSystem", "PV1", True, ("kvar",)),
        InventoryObject("Storage.B1", "Storage", "B1", True, ("kW", "kvar")),
        InventoryObject("Transformer.RegX", "Transformer", "RegX", True, ()),
        InventoryObject("Line.SW1", "Line", "SW1", True, ()),
        InventoryObject("Load.L1", "Load", "L1", True, ("kW",)),
    )
    inventory = CircuitInventory(
        schema_version=INVENTORY_SCHEMA_VERSION,
        relationship_schema_version=CONTROL_RELATIONSHIP_SCHEMA_VERSION,
        discovery_schema_version="A02.discovery.v1",
        backend="altdss",
        altdss_version="0.2.4",
        engine_version="test-engine",
        master_relative_path="Master.dss",
        master_sha256="A" * 64,
        source_tree_sha256="B" * 64,
        source_dependencies=(),
        circuit_name="test",
        num_buses=2,
        num_nodes=6,
        num_circuit_elements=len(objects),
        a02_discovery_semantic_sha256="C" * 64,
        buses=(
            InventoryBus("b1", ("b1.1", "b1.2", "b1.3")),
            InventoryBus("b2", ("b2.1", "b2.2", "b2.3")),
        ),
        node_names=("b1.1", "b1.2", "b1.3", "b2.1", "b2.2", "b2.3"),
        classes=(
            InventoryClass("PVSystem", ("PVSystem.PV1",)),
            InventoryClass("Storage", ("Storage.B1",)),
            InventoryClass("Transformer", ("Transformer.RegX",)),
            InventoryClass("Line", ("Line.SW1",)),
            InventoryClass("Load", ("Load.L1",)),
        ),
        objects=objects,
        elements=(),
        native_control_catalog=(),
        native_controls=(),
        control_relationships=(),
    )

    entries = []
    states = []
    actions = []
    disturbances = []
    parameters = []
    constraints = []

    for bus in ("b2", "b1"):
        item = entry(
            RuntimeReadoutAddress("Bus", bus, "voltage"),
            "bus_voltage",
            entity=f"Bus.{bus}",
            dtype="complex",
            shape=(3,),
            unit="V",
            tags=("observation.bus_voltage",),
        )
        entries.append(item); states.append(item.semantic_id)

    converged = entry(
        RuntimeReadoutAddress("Solution", None, "converged"),
        "solution_converged",
        dtype="bool",
        tags=("service.snapshot_solve",),
    )
    entries.append(converged); states.append(converged.semantic_id)

    load = entry(
        NativePropertyAddress("Load.L1", "kW"),
        "load_active_power_driver",
        entity="Load.L1",
        mutability=Mutability.STEP_EXOGENOUS,
        unit="kW",
        tags=("disturbance.load_power",),
    )
    entries.append(load); disturbances.append(load.semantic_id)

    def add_parameter(entity, prop, value, constraint=False):
        dss_class = entity.split(".", 1)[0]
        item = entry(
            NativePropertyAddress(entity, prop),
            f"{dss_class}.{prop}",
            entity=entity,
            mutability=Mutability.INIT_ONLY,
            metadata={"compile_time_value": value},
        )
        entries.append(item); parameters.append(item.semantic_id)
        if constraint:
            constraints.append(item.semantic_id)
        return item

    add_parameter("PVSystem.PV1", "kVA", 75.0, True)
    add_parameter("PVSystem.PV1", "kvarMax", 50.0, True)
    add_parameter("PVSystem.PV1", "kvarMaxAbs", 60.0, True)
    add_parameter("Storage.B1", "kWRated", 100.0, True)
    add_parameter("Storage.B1", "kVA", 120.0, True)
    add_parameter("Storage.B1", "kvarMax", 80.0, True)
    add_parameter("Storage.B1", "kvarMaxAbs", 90.0, True)
    add_parameter("Transformer.RegX", "MinTap", [0.9, 0.9], True)
    add_parameter("Transformer.RegX", "MaxTap", [1.1, 1.1], True)

    action_specs = (
        (
            NativePropertyAddress("PVSystem.PV1", "kvar"),
            "pv_reactive_power_command", "PVSystem.PV1", "float", {}, "kvar",
        ),
        (
            NativePropertyAddress("Storage.B1", "kW"),
            "storage_active_power_command", "Storage.B1", "float", {}, "kW",
        ),
        (
            RuntimeCommandAddress("Transformer", "Transformer.RegX", "set_tap"),
            "transformer_tap_command", "Transformer.RegX", "float", {}, None,
        ),
        (
            RuntimeCommandAddress("CircuitElement", "Line.SW1", "open_close"),
            "branch_switch_command", "Line.SW1", "enum", {"allowed_states": ["OPEN", "CLOSED"]}, None,
        ),
    )
    for address, quantity, entity_name, dtype, meta, unit in action_specs:
        item = entry(
            address,
            quantity,
            entity=entity_name,
            dtype=dtype,
            mutability=Mutability.STEP_CONTROLLABLE,
            metadata=meta,
            unit=unit,
            tags=("control.test",),
        )
        entries.append(item); actions.append(item.semantic_id)

    entries = tuple(entries)
    classes = tuple(
        CircuitClassRecord(item.dss_class, item.object_full_names)
        for item in inventory.classes
    )
    bundle = SemanticRegistryBundle(
        registry_schema_version=SEMANTIC_REGISTRY_SCHEMA_VERSION,
        semantic_policy_version=SEMANTIC_POLICY_VERSION,
        semantic_policy_sha256="D" * 64,
        source_inventory_semantic_sha256=inventory.semantic_sha256,
        source_tree_sha256=inventory.source_tree_sha256,
        backend="altdss",
        altdss_version="0.2.4",
        engine_version="test-engine",
        semantic_entries=entries,
        circuit_registry=CircuitRegistry(
            inventory.circuit_name,
            tuple(bus.name for bus in inventory.buses),
            inventory.node_names,
            classes,
            tuple(item.full_name for item in inventory.objects),
            (),
        ),
        state_registry=StateRegistry(tuple(states)),
        action_registry=ActionRegistry(tuple(actions)),
        disturbance_registry=DisturbanceRegistry(tuple(disturbances)),
        constraint_registry=ConstraintRegistry(tuple(constraints)),
        parameter_registry=ParameterRegistry(tuple(parameters)),
        capability_registry=CapabilityRegistry(
            (
                CapabilityRecord("observation.bus_voltage", tuple(states[:2]), ("Bus.b1", "Bus.b2")),
                CapabilityRecord("control.test", tuple(actions), tuple(item.native_entity for item in entries if item.semantic_id in actions and item.native_entity)),
                CapabilityRecord("disturbance.load_power", (load.semantic_id,), ("Load.L1",)),
            )
        ),
    )
    return inventory, bundle


def first_id(bundle, registry: RegistryKind, quantity: str):
    ids = {
        RegistryKind.STATE: bundle.state_registry.entry_ids,
        RegistryKind.ACTION: bundle.action_registry.entry_ids,
        RegistryKind.DISTURBANCE: bundle.disturbance_registry.entry_ids,
        RegistryKind.CONSTRAINT: bundle.constraint_registry.entry_ids,
        RegistryKind.PARAMETER: bundle.parameter_registry.entry_ids,
    }[registry]
    lookup = bundle.entry_by_id()
    return next(item for item in ids if lookup[item].quantity == quantity)
