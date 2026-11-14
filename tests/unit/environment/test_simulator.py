from pathlib import Path

import pytest

from opendsssim.environment.simulator import OpenDSSSimulator


FIXTURE = Path(__file__).parents[2] / "fixtures" / "a01_minimal" / "Master.dss"


def test_minimal_gymnasium_reset_and_step():
    env = OpenDSSSimulator(FIXTURE)
    try:
        obs, info = env.reset(seed=7)
        assert env.observation_space.contains(obs)
        assert obs["converged"] == 1
        assert info["solution"]["converged"] is True

        obs2, reward, terminated, truncated, info2 = env.step({})
        assert env.observation_space.contains(obs2)
        assert reward == 0.0
        assert terminated is False
        assert truncated is False
        assert info2["solution"]["converged"] is True
    finally:
        env.close()


def test_a01_rejects_nonempty_action():
    env = OpenDSSSimulator(FIXTURE)
    try:
        env.reset()
        with pytest.raises(ValueError):
            env.step({"not_allowed": 1})
    finally:
        env.close()
