import json

from opendsssim.discovery.native_controls import (
    NATIVE_CONTROL_CLASSES,
    discover_native_controls,
)
from opendsssim.discovery.schema import (
    CircuitDiscovery,
    DSSObjectDiscovery,
    EngineDiscovery,
    TopologyDiscovery,
)


def _obj(full_name, dss_class, props):
    name = full_name.split(".", 1)[1]
    payload = {"Name": name, "DSSClass": dss_class, **props}
    return DSSObjectDiscovery(
        full_name=full_name,
        dss_class=dss_class,
        name=name,
        is_circuit_element=True,
        property_names=tuple(sorted(payload)),
        properties_json=json.dumps(payload, sort_keys=True),
    )


def _discovery(objects):
    return CircuitDiscovery(
        schema_version="A02.v1",
        source_sha256="A" * 64,
        circuit_name="controltest",
        num_buses=1,
        num_nodes=1,
        num_circuit_elements=len(objects),
        solution_converged=False,
        engine=EngineDiscovery(
            schema_version="A02.v1",
            backend="altdss",
            altdss_version="0.2.4",
            engine_version="engine",
            context_identity=1,
            public_api_names=(),
            feature_flags=(),
        ),
        buses=(),
        node_names=(),
        classes=(),
        objects=tuple(objects),
        elements=(),
        topology=TopologyDiscovery(
            isolated_branches=(),
            isolated_loads=(),
            looped_pairs=(),
            num_isolated_branches=0,
            num_isolated_loads=0,
            num_loops=0,
        ),
    )


def test_official_control_catalog_is_complete_for_a02h1_contract():
    assert NATIVE_CONTROL_CLASSES == (
        "CapControl",
        "ESPVLControl",
        "ExpControl",
        "Fuse",
        "GenDispatcher",
        "InvControl",
        "Recloser",
        "RegControl",
        "Relay",
        "StorageController",
        "SwtControl",
        "UPFCControl",
    )


def test_native_control_relationships_preserve_native_names_and_defaults():
    objects = [
        _obj("Transformer.RegX", "Transformer", {}),
        _obj("Line.Feeder", "Line", {}),
        _obj("Capacitor.Cap1", "Capacitor", {}),
        _obj("PVSystem.PV1", "PVSystem", {}),
        _obj(
            "RegControl.RC1",
            "RegControl",
            {"Transformer": "RegX", "Winding": 2, "TapWinding": 2},
        ),
        _obj(
            "CapControl.CC1",
            "CapControl",
            {"Element": "Line.Feeder", "Terminal": 2, "Capacitor": "Cap1"},
        ),
        _obj("InvControl.IC1", "InvControl", {"DERList": []}),
        _obj(
            "Relay.RL1",
            "Relay",
            {"MonitoredObj": "Line.Feeder", "MonitoredTerm": 1},
        ),
    ]

    controls, relationships = discover_native_controls(_discovery(objects))

    assert {item.full_name for item in controls} == {
        "RegControl.RC1",
        "CapControl.CC1",
        "InvControl.IC1",
        "Relay.RL1",
    }

    triples = {
        (item.source_full_name, item.role, item.target_full_name)
        for item in relationships
    }
    assert ("RegControl.RC1", "CONTROLS", "Transformer.RegX") in triples
    assert ("CapControl.CC1", "MONITORS", "Line.Feeder") in triples
    assert ("CapControl.CC1", "CONTROLS", "Capacitor.Cap1") in triples
    assert ("InvControl.IC1", "CONTROLS", "PVSystem.PV1") in triples
    assert ("Relay.RL1", "MONITORS", "Line.Feeder") in triples
    assert ("Relay.RL1", "PROTECTS", "Line.Feeder") in triples

    relay_default = next(
        item
        for item in relationships
        if item.source_full_name == "Relay.RL1" and item.role == "PROTECTS"
    )
    assert relay_default.resolution == "ENGINE_DEFAULT_MONITORED_OBJECT"
