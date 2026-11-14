from pathlib import Path

import pytest

from opendsssim.environment.simulator import OpenDSSSimulator


FIXTURE = Path(__file__).parents[1] / "fixtures" / "a01_minimal" / "Master.dss"


def test_reset_reuses_context_and_reproduces_electrical_result():
    env = OpenDSSSimulator(FIXTURE)
    try:
        context_before = env.context_identity
        _, info1 = env.reset(seed=1)
        _, info2 = env.reset(seed=1)
        context_after = env.context_identity

        s1 = info1["solution"]
        s2 = info2["solution"]

        assert context_before == context_after
        assert s1["circuit_name"] == s2["circuit_name"]
        assert s1["num_buses"] == s2["num_buses"]
        assert s1["num_nodes"] == s2["num_nodes"]
        assert s1["num_circuit_elements"] == s2["num_circuit_elements"]
        assert s1["total_power_kw"] == pytest.approx(s2["total_power_kw"], rel=0, abs=1e-9)
        assert s1["total_power_kvar"] == pytest.approx(s2["total_power_kvar"], rel=0, abs=1e-9)
    finally:
        env.close()
