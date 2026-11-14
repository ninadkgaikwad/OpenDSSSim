import json

from opendsssim.discovery.schema import (
    DISCOVERY_SCHEMA_VERSION,
    BusDiscovery,
    CircuitDiscovery,
    EngineDiscovery,
    TopologyDiscovery,
)


def test_discovery_schema_is_json_serializable_and_context_independent():
    engine_a = EngineDiscovery(
        schema_version=DISCOVERY_SCHEMA_VERSION,
        backend="altdss",
        altdss_version="0.2.4",
        engine_version="engine",
        context_identity=100,
        public_api_names=("BusNames", "Element"),
        feature_flags=("bus_inventory",),
    )
    engine_b = EngineDiscovery(
        schema_version=DISCOVERY_SCHEMA_VERSION,
        backend="altdss",
        altdss_version="0.2.4",
        engine_version="engine",
        context_identity=200,
        public_api_names=("BusNames", "Element"),
        feature_flags=("bus_inventory",),
    )

    kwargs = dict(
        schema_version=DISCOVERY_SCHEMA_VERSION,
        source_sha256="A" * 64,
        circuit_name="test",
        num_buses=1,
        num_nodes=1,
        num_circuit_elements=0,
        solution_converged=True,
        buses=(BusDiscovery(name="bus", node_names=("bus.1",)),),
        node_names=("bus.1",),
        classes=(),
        objects=(),
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

    a = CircuitDiscovery(engine=engine_a, **kwargs)
    b = CircuitDiscovery(engine=engine_b, **kwargs)

    assert json.loads(a.to_json())["circuit_name"] == "test"
    assert a.semantic_sha256 == b.semantic_sha256
    assert a.to_dict() != b.to_dict()
