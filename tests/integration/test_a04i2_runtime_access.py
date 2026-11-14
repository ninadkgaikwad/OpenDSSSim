from __future__ import annotations

import math
from pathlib import Path

import pytest

from opendsssim.backends.altdss_backend import AltDSSBackend
from opendsssim.backends.base import OpenDSSSimBackendError
from opendsssim.network.loading import CircuitSource
from opendsssim.runtime import SemanticRuntimeAccess
from opendsssim.semantics.schema import (
    NativePropertyAddress,
    RuntimeCommandAddress,
    RuntimeReadoutAddress,
)


FIXTURE = Path(__file__).parents[1] / "fixtures" / "a03_semantic" / "Master.dss"


def _live_backend() -> AltDSSBackend:
    backend = AltDSSBackend()
    backend.load_circuit(CircuitSource.from_path(FIXTURE))
    result = backend.solve_snapshot()
    assert result.converged
    return backend


def test_a04i2_native_property_read_write_and_enabled_roundtrip():
    backend = _live_backend()
    access = SemanticRuntimeAccess(backend)
    try:
        context_id = backend.context_identity

        pv_q = NativePropertyAddress("PVSystem.PV1", "kvar")
        original_q = float(access.read(pv_q))
        written_q = float(access.write(pv_q, 12.5))
        assert written_q == pytest.approx(12.5)
        assert float(access.read(pv_q)) == pytest.approx(12.5)
        access.write(pv_q, original_q)

        enabled = NativePropertyAddress("Line.Feeder", "Enabled")
        assert bool(access.read(enabled)) is True
        assert bool(access.write(enabled, False)) is False
        assert bool(access.read(enabled)) is False
        assert bool(access.write(enabled, True)) is True

        assert backend.context_identity == context_id
    finally:
        backend.close()


def test_a04i2_bus_and_element_runtime_readouts_are_genuine():
    backend = _live_backend()
    access = SemanticRuntimeAccess(backend)
    try:
        volts = access.read(RuntimeReadoutAddress("Bus", "source", "voltage"))
        pu = access.read(RuntimeReadoutAddress("Bus", "source", "pu_voltage"))
        assert len(volts) == len(pu) >= 1
        assert all(isinstance(value, complex) for value in volts)
        assert all(isinstance(value, float) and math.isfinite(value) for value in pu)
        assert all(value >= 0.0 for value in pu)

        currents = access.read(
            RuntimeReadoutAddress("CircuitElement", "Line.Feeder", "currents")
        )
        terminal_power = access.read(
            RuntimeReadoutAddress("CircuitElement", "Line.Feeder", "terminal_power")
        )
        losses = access.read(
            RuntimeReadoutAddress("CircuitElement", "Line.Feeder", "losses")
        )
        open_state = access.read(
            RuntimeReadoutAddress("CircuitElement", "Line.Feeder", "open_state")
        )

        assert len(currents) >= 1
        assert all(isinstance(value, complex) for value in currents)
        assert len(terminal_power) == 2
        assert all(isinstance(value, complex) for value in terminal_power)
        assert isinstance(losses, complex)
        assert open_state == (False, False)

        converged = access.read(RuntimeReadoutAddress("Solution", None, "converged"))
        assert converged is True

        topology = access.read(RuntimeReadoutAddress("Topology", None, "connectivity"))
        assert set(topology) == {
            "isolated_branches",
            "isolated_loads",
            "looped_pairs",
            "num_isolated_branches",
            "num_isolated_loads",
            "num_loops",
        }
    finally:
        backend.close()


def test_a04i2_transformer_tap_readout_and_command_persist_with_native_control_disabled():
    backend = _live_backend()
    access = SemanticRuntimeAccess(backend)
    try:
        context_id = backend.context_identity

        # A04I2 only provides the primitive. Authority configuration itself is A04I3.
        # Disable the fixture's native regulator explicitly so it cannot overwrite
        # the external tap command during the qualification solve.
        assert bool(
            access.write(NativePropertyAddress("RegControl.RC1", "Enabled"), False)
        ) is False

        tap_address = RuntimeReadoutAddress("Transformer", "Transformer.RegX", "taps")
        taps_before = access.read(tap_address)
        assert len(taps_before) == 2

        target = 1.025
        returned = access.write(
            RuntimeCommandAddress("Transformer", "Transformer.RegX", "set_tap"),
            target,
        )
        assert len(returned) == 2
        assert returned[1] == pytest.approx(target)
        assert returned[0] == pytest.approx(taps_before[0])

        solved = backend.solve_snapshot()
        assert solved.converged
        taps_after = access.read(tap_address)
        assert taps_after[1] == pytest.approx(target)
        assert backend.context_identity == context_id
    finally:
        backend.close()


def test_a04i2_switch_open_close_command_is_genuine_and_context_persistent():
    backend = _live_backend()
    access = SemanticRuntimeAccess(backend)
    try:
        context_id = backend.context_identity

        # Prevent the fixture SwtControl from undoing explicit external switching
        # during the qualification sequence. A04I3 will own authority setup.
        assert bool(
            access.write(NativePropertyAddress("SwtControl.SC1", "Enabled"), False)
        ) is False

        command = RuntimeCommandAddress("CircuitElement", "Line.Feeder", "open_close")
        state = RuntimeReadoutAddress("CircuitElement", "Line.Feeder", "open_state")

        opened = access.write(command, "OPEN")
        assert opened[0] is True
        assert access.read(state)[0] is True

        closed = access.write(command, "CLOSED")
        assert closed[0] is False
        assert access.read(state)[0] is False

        assert backend.context_identity == context_id
    finally:
        backend.close()


def test_a04i2_runtime_access_fails_closed_for_unsupported_vocabulary():
    backend = _live_backend()
    try:
        with pytest.raises(OpenDSSSimBackendError, match="Unsupported A03 runtime readout"):
            backend.read_runtime_channel("Bus", "source", "not_a_channel")
        with pytest.raises(OpenDSSSimBackendError, match="Unsupported A03 runtime command"):
            backend.apply_runtime_command("CircuitElement", "Line.Feeder", "not_a_command", 1)
    finally:
        backend.close()
