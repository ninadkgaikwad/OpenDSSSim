from pathlib import Path

from opendsssim.environment.simulator import OpenDSSSimulator


FIXTURE = Path(__file__).parents[1] / "fixtures" / "a01_minimal" / "Master.dss"


def test_two_environments_own_distinct_contexts():
    env_a = OpenDSSSimulator(FIXTURE)
    env_b = OpenDSSSimulator(FIXTURE)
    try:
        assert env_a.context_identity != env_b.context_identity
        _, info_a = env_a.reset()
        _, info_b = env_b.reset()
        assert info_a["solution"]["context_identity"] != info_b["solution"]["context_identity"]
        assert info_a["solution"]["converged"]
        assert info_b["solution"]["converged"]
    finally:
        env_a.close()
        env_b.close()
