import json
from pathlib import Path

import pytest

from opendsssim.backends.altdss_backend import AltDSSBackend
from opendsssim.backends.base import CircuitNotLoadedError
from opendsssim.network.loading import CircuitSource


FIXTURE = Path(__file__).parents[2] / "fixtures" / "a01_minimal" / "Master.dss"


def test_backend_discovery_requires_loaded_circuit():
    backend = AltDSSBackend()
    try:
        engine = backend.discover_engine()
        assert engine.backend == "altdss"
        with pytest.raises(CircuitNotLoadedError):
            backend.discover_circuit()
    finally:
        backend.close()


def test_backend_discovers_native_objects_and_structure():
    backend = AltDSSBackend()
    try:
        backend.load_circuit(CircuitSource.from_path(FIXTURE))
        backend.solve_snapshot()
        discovery = backend.discover_circuit()

        assert discovery.num_buses >= 2
        assert len(discovery.elements) == discovery.num_circuit_elements

        names = {obj.full_name.casefold() for obj in discovery.objects}
        assert "load.load1" in names
        assert "line.feeder" in names

        load = next(
            obj
            for obj in discovery.objects
            if obj.full_name.casefold() == "load.load1"
        )
        props = json.loads(load.properties_json)
        assert isinstance(props, dict)
        assert any(name.casefold() == "bus1" for name in load.property_names)

        feeder = next(
            element
            for element in discovery.elements
            if element.full_name.casefold() == "line.feeder"
        )
        assert feeder.num_phases == 3
        assert feeder.num_terminals >= 2
        assert feeder.num_conductors >= 3
        assert feeder.terminal_bus_specs
    finally:
        backend.close()
