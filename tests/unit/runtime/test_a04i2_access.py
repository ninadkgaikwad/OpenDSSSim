from __future__ import annotations

from typing import Any

import pytest

from opendsssim.backends.base import DistributionBackend
from opendsssim.runtime.access import SemanticRuntimeAccess, SemanticRuntimeAccessError
from opendsssim.semantics.schema import (
    NativePropertyAddress,
    RuntimeCommandAddress,
    RuntimeReadoutAddress,
)


class RecordingBackend(DistributionBackend):
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self._closed = False

    @property
    def context_identity(self) -> int:
        return 1

    @property
    def engine_version(self) -> str:
        return "fake"

    @property
    def loaded_source(self):
        return None

    @property
    def is_closed(self) -> bool:
        return self._closed

    def load_circuit(self, source):  # pragma: no cover - not used here
        raise NotImplementedError

    def reset_circuit(self):  # pragma: no cover - not used here
        raise NotImplementedError

    def solve_snapshot(self):  # pragma: no cover - not used here
        raise NotImplementedError

    def discover_engine(self):  # pragma: no cover - not used here
        raise NotImplementedError

    def discover_circuit(self):  # pragma: no cover - not used here
        raise NotImplementedError

    def read_object_properties(self, object_full_name, property_names):
        self.calls.append(("read_property", object_full_name, property_names))
        return {"kvar": 12.5}

    def write_object_property(self, object_full_name, property_name, value):
        self.calls.append(("write_property", object_full_name, property_name, value))
        return value

    def read_runtime_channel(self, service, entity, channel):
        self.calls.append(("read_runtime", service, entity, channel))
        return (1.0, 2.0)

    def apply_runtime_command(self, service, entity, operation, value):
        self.calls.append(("command", service, entity, operation, value))
        return value

    def close(self) -> None:
        self._closed = True


def test_native_property_read_and_write_dispatch():
    backend = RecordingBackend()
    access = SemanticRuntimeAccess(backend)
    address = NativePropertyAddress("PVSystem.PV1", "kvar")

    assert access.read(address) == 12.5
    assert access.write(address, 20.0) == 20.0
    assert backend.calls == [
        ("read_property", "PVSystem.PV1", ("kvar",)),
        ("write_property", "PVSystem.PV1", "kvar", 20.0),
    ]


def test_native_property_read_is_case_insensitive_to_backend_key():
    backend = RecordingBackend()
    access = SemanticRuntimeAccess(backend)
    assert access.read(NativePropertyAddress("PVSystem.PV1", "KVAR")) == 12.5


def test_runtime_readout_dispatch():
    backend = RecordingBackend()
    access = SemanticRuntimeAccess(backend)
    address = RuntimeReadoutAddress("Bus", "source", "voltage")

    assert access.read(address) == (1.0, 2.0)
    assert backend.calls[-1] == ("read_runtime", "Bus", "source", "voltage")


def test_runtime_command_dispatch():
    backend = RecordingBackend()
    access = SemanticRuntimeAccess(backend)
    address = RuntimeCommandAddress("CircuitElement", "Line.Feeder", "open_close")

    assert access.write(address, "OPEN") == "OPEN"
    assert backend.calls[-1] == (
        "command",
        "CircuitElement",
        "Line.Feeder",
        "open_close",
        "OPEN",
    )


def test_runtime_command_is_not_directly_readable():
    access = SemanticRuntimeAccess(RecordingBackend())
    with pytest.raises(SemanticRuntimeAccessError, match="write-only"):
        access.read(RuntimeCommandAddress("Transformer", "Transformer.RegX", "set_tap"))


def test_runtime_readout_is_not_writable():
    access = SemanticRuntimeAccess(RecordingBackend())
    with pytest.raises(SemanticRuntimeAccessError, match="read-only"):
        access.write(RuntimeReadoutAddress("Solution", None, "converged"), True)
