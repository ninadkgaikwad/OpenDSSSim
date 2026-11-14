from pathlib import Path

from opendsssim.backends.altdss_backend import AltDSSBackend
from opendsssim.network.loading import CircuitSource


FIXTURE = Path(__file__).parents[1] / "fixtures" / "a01_minimal" / "Master.dss"


def test_snapshot_solution_contract():
    backend = AltDSSBackend()
    try:
        backend.load_circuit(CircuitSource.from_path(FIXTURE))
        result = backend.solve_snapshot()
        assert result.converged
        assert result.solve_mode
        assert result.iterations >= 1
        assert result.total_iterations >= result.iterations
        assert result.num_buses >= 2
        assert result.num_nodes >= 4
        assert result.num_circuit_elements >= 2
        assert abs(result.total_power_kw) > 0.0
    finally:
        backend.close()
