from pathlib import Path

import pytest

from opendsssim.backends.altdss_backend import AltDSSBackend
from opendsssim.backends.base import CircuitNotLoadedError
from opendsssim.network.loading import CircuitSource


FIXTURE = Path(__file__).parents[2] / "fixtures" / "a01_minimal" / "Master.dss"


def test_backend_requires_circuit_before_solve():
    backend = AltDSSBackend()
    try:
        with pytest.raises(CircuitNotLoadedError):
            backend.solve_snapshot()
    finally:
        backend.close()


def test_backend_load_and_snapshot_solve():
    backend = AltDSSBackend()
    try:
        identity = backend.load_circuit(CircuitSource.from_path(FIXTURE))
        result = backend.solve_snapshot()
        assert identity.circuit_name
        assert result.converged
        assert result.num_buses >= 2
        assert result.num_circuit_elements >= 2
        assert result.altdss_version == "0.2.4"
    finally:
        backend.close()


def test_backend_close_is_idempotent():
    backend = AltDSSBackend()
    backend.close()
    backend.close()
    assert backend.is_closed
