from pathlib import Path

from opendsssim.environment.simulator import OpenDSSSimulator


FIXTURE = Path(__file__).parents[1] / "fixtures" / "a01_minimal" / "Master.dss"


def test_discovery_is_deterministic_read_only_and_context_isolated():
    env_a = OpenDSSSimulator(FIXTURE)
    env_b = OpenDSSSimulator(FIXTURE)

    try:
        env_a.reset(seed=3)
        env_b.reset(seed=3)

        solution_before = env_a.last_result.to_dict()

        first = env_a.discover_circuit()
        second = env_a.discover_circuit()
        other = env_b.discover_circuit()

        solution_after = env_a.last_result.to_dict()

        assert solution_before == solution_after
        assert first.to_dict() == second.to_dict()
        assert first.semantic_sha256 == second.semantic_sha256
        assert first.semantic_sha256 == other.semantic_sha256
        assert first.engine.context_identity != other.engine.context_identity

        _, _, terminated, truncated, info = env_a.step({})
        assert terminated is False
        assert truncated is False
        assert info["solution"]["converged"] is True
    finally:
        env_a.close()
        env_b.close()
