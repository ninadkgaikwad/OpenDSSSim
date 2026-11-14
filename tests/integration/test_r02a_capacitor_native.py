"""R02A true AltDSS regression: capacitor state/readback and repeatability."""

import json
from pathlib import Path

import pytest

from opendsssim.backends.altdss_backend import AltDSSBackend
from opendsssim.network.loading import CircuitSource

REPO = Path(__file__).resolve().parents[2]
SEMANTIC = REPO / "tests" / "fixtures" / "a03_semantic" / "Master.dss"
BASE = REPO / "experiments" / "pesgm2027" / "feeders" / "ieee123_base" / "IEEE123Master.dss"
WORKING = REPO / "experiments" / "pesgm2027" / "feeders" / "ieee123_pesgm2027" / "IEEE123Master.dss"


def _capacitors(discovery):
    return {
        item.full_name.casefold(): json.loads(item.properties_json)
        for item in discovery.objects
        if item.dss_class.casefold() == "capacitor"
    }


def test_semantic_fixture_repeated_contexts_have_identical_capacitor_discovery():
    seen = []
    for _ in range(12):
        backend = AltDSSBackend()
        try:
            backend.load_circuit(CircuitSource.from_path(SEMANTIC))
            first = _capacitors(backend.discover_circuit())
            second = _capacitors(backend.discover_circuit())
            assert first == second
            cap = first["capacitor.cap1"]
            assert "CMatrix" not in cap  # not configured in the fixture
            assert cap["States"] == [1]
            assert cap["Enabled"] is True
            assert "NormAmps" in cap and "EmergAmps" in cap
            assert cap["kvar"] == [300.0]
            seen.append(first)
        finally:
            backend.close()
    assert all(item == seen[0] for item in seen)


@pytest.mark.parametrize("master", [BASE, WORKING], ids=["canonical_ieee123", "working_ieee123"])
def test_genuine_ieee123_capacitor_discovery_and_native_readback(master):
    backend = AltDSSBackend()
    try:
        backend.load_circuit(CircuitSource.from_path(master))
        snap = backend.discover_circuit()
        caps = _capacitors(snap)
        assert len(caps) >= 1
        for full_name, properties in caps.items():
            assert isinstance(properties["States"], list)
            assert isinstance(properties["Enabled"], bool)
            assert properties["kvar"]
            assert "NormAmps" in properties
            actual = backend.read_object_properties(
                full_name, ("States", "Enabled", "kvar", "NormAmps", "EmergAmps")
            )
            assert actual["States"] == properties["States"]
            assert actual["Enabled"] == properties["Enabled"]
        # Circuit discovery remains read-only; physical power-flow remains native.
        result = backend.solve_snapshot()
        assert result.converged
    finally:
        backend.close()
