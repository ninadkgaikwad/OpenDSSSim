"""R02A: safe typed capacitor discovery, without relaxing malformed-input handling."""

import json
import pytest

from opendsssim.backends.altdss_backend import (
    _CAPACITOR_SPARSE_FLAGS,
    _DISCOVERY_JSON_FLAGS,
    _read_discovery_properties,
)
from opendsssim.backends.base import OpenDSSSimBackendError


class SyntheticCapacitor:
    def __init__(self, *, explicit=None, invalid_sparse=False, missing_getter=None):
        self.explicit = explicit or {
            "Name": "cap1", "Bus1": "regbus.1.2.3", "Phases": 3,
            "kV": 12.47, "kvar": [300.0],
        }
        self.invalid_sparse = invalid_sparse
        self.missing_getter = missing_getter
        self.requested_flags = []
        self.data = {
            "Bus1": "regbus.1.2.3", "Bus2": "regbus.0.0.0",
            "Phases": 3, "kvar": [300.0], "kV": 12.47,
            "Conn_str": "wye", "Cuf": [5.1], "R": [0.0],
            "XL": [0.0], "Harm": [0.0], "States": [1],
            "NormAmps": 18.75, "EmergAmps": 25.0,
            "FaultRate": 0.0005, "pctPerm": 100.0,
            "Repair": 3.0, "BaseFreq": 60.0, "Enabled": True,
        }

    def to_json(self, flags):
        self.requested_flags.append(flags)
        if flags == _DISCOVERY_JSON_FLAGS:
            raise AssertionError("Capacitor must not use Full native serialization")
        assert flags == _CAPACITOR_SPARSE_FLAGS
        if self.invalid_sparse:
            return '{"Name":"cap1","CMatrix":[nonsense]}'
        return json.dumps(self.explicit)

    def __getattr__(self, name):
        if name == self.missing_getter or name not in self.data:
            raise AttributeError(name)
        return self.data[name]


def test_synthetic_capacitor_avoids_unused_cmatrix_and_preserves_native_defaults():
    obj = SyntheticCapacitor()
    first = _read_discovery_properties(obj, "Capacitor.cap1")
    second = _read_discovery_properties(obj, "Capacitor.cap1")
    assert first == second
    assert "CMatrix" not in first
    assert first["kvar"] == [300.0]
    assert first["States"] == [1]
    assert first["Enabled"] is True
    assert first["Conn"] == "wye"
    assert first["Bus2"] == "regbus.0.0.0"
    assert first["NormAmps"] == 18.75
    assert obj.requested_flags == [_CAPACITOR_SPARSE_FLAGS] * 2


def test_explicit_capacitor_matrix_is_retained_not_discarded():
    raw = {"Name": "cap1", "Bus1": "regbus.1.2.3", "CMatrix": [[1.2, 0.0], [0.0, 2.1]]}
    result = _read_discovery_properties(SyntheticCapacitor(explicit=raw), "Capacitor.cap1")
    assert result["CMatrix"] == raw["CMatrix"]


@pytest.mark.parametrize("bad", [
    {"Name": "incorrect"},
    {"Name": "cap1", "DSSClass": "Reactor"},
    {"Name": "cap1", "CMatrix": [[float("nan")]]},
])
def test_inconsistent_or_nonfinite_explicit_native_values_fail_closed(bad):
    with pytest.raises(OpenDSSSimBackendError):
        _read_discovery_properties(SyntheticCapacitor(explicit=bad), "Capacitor.cap1")


def test_malformed_explicit_json_fails_closed():
    with pytest.raises(OpenDSSSimBackendError):
        _read_discovery_properties(SyntheticCapacitor(invalid_sparse=True), "Capacitor.cap1")


def test_missing_native_property_getter_fails_closed():
    with pytest.raises(OpenDSSSimBackendError, match="Missing native capacitor getter"):
        _read_discovery_properties(SyntheticCapacitor(missing_getter="States"), "Capacitor.cap1")


def test_other_classes_keep_existing_full_native_json_path():
    class NativeLoad:
        def to_json(self, flags):
            assert flags == _DISCOVERY_JSON_FLAGS
            return '{"DSSClass":"Load","Name":"load1","kW":100}'

    assert _read_discovery_properties(NativeLoad(), "Load.load1")["kW"] == 100
