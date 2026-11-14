"""Genuine AltDSS IEEE123 acceptance for narrow external-clock stage."""
from pathlib import Path

import pytest

from opendsssim.environment import EpisodeSpec, OpenDSSSimulator
from opendsssim.problem import ObservationSpec, ProblemSpec, RegistryKind, SelectionGroup, SemanticQuery
from opendsssim.runtime import HistoryLevel


REPO = Path(__file__).resolve().parents[2]
FEEDERS = REPO / "experiments" / "pesgm2027" / "feeders"


def _native_problem() -> ProblemSpec:
    return ProblemSpec.create("a05i1a-native-time", "1", observations=ObservationSpec(
        groups=(SelectionGroup("obs", (SemanticQuery(RegistryKind.STATE, quantity="solution_converged"),)),)
    ))


@pytest.mark.parametrize("feeder", ["ieee123_base", "ieee123_pesgm2027"])
def test_ieee123_option_a_horizon_and_native_snapshot(tmp_path, feeder):
    master = FEEDERS / feeder / "IEEE123Master.dss"
    assert master.is_file(), f"Real repo IEEE123 fixture missing: {master}"
    env = OpenDSSSimulator(master, problem=_native_problem(),
                           episode_spec=EpisodeSpec(dt_seconds=1800, max_steps=2),
                           history_level=HistoryLevel.H0,
                           inventory_dir=tmp_path / "inv", semantic_registry_dir=tmp_path / "sem",
                           preflight_dir=tmp_path / "preflight")
    try:
        context_id = env.context_identity
        original = env._plant.backend.solve_snapshot
        calls = 0

        def counted():
            nonlocal calls
            calls += 1
            return original()

        env._plant.backend.solve_snapshot = counted
        obs, reset_info = env.reset(seed=41)
        assert calls == 1
        assert reset_info["solution"]["converged"] is True
        assert env.observation_space.contains(obs)
        assert len(env.history) == 1
        assert env.history[0]["time"]["completed_steps"] == 0

        first_sample = reset_info["time"]["electrical_sample_time_utc"]
        obs1, reward1, term1, trunc1, info1 = env.step({})
        assert env.observation_space.contains(obs1)
        assert info1["solution"]["converged"] is True
        assert calls == 2 and env.context_identity == context_id
        assert (reward1, term1, trunc1) == (0.0, False, False)
        assert info1["time"]["electrical_sample_time_utc"] == first_sample
        assert info1["time"]["decision_time_utc"] != first_sample
        assert env.history[1]["time"] == info1["time"]

        _, reward2, term2, trunc2, info2 = env.step({})
        assert (reward2, term2, trunc2) == (0.0, False, True)
        assert info2["solution"]["converged"] is True
        assert info2["time"]["electrical_sample_time_utc"] == info1["time"]["decision_time_utc"]
        assert calls == 3 and len(env.history) == 3
        with pytest.raises(RuntimeError, match="reset"):
            env.step({})
        assert calls == 3

        obs_new, info_new = env.reset(options={"max_steps": 1, "start_time_utc": "2026-10-28T00:00:00Z"})
        assert env.observation_space.contains(obs_new)
        assert info_new["time"]["t0_utc"] == "2026-10-28T00:00:00+00:00"
        assert env.context_identity == context_id
        assert calls == 4 and len(env.history) == 1
        _, _, _, truncated, _ = env.step({})
        assert truncated and calls == 5
    finally:
        env.close()


def test_ieee123_backend_failure_locks_episode_until_reset(tmp_path):
    env = OpenDSSSimulator(FEEDERS / "ieee123_base" / "IEEE123Master.dss",
                           episode_spec=EpisodeSpec(max_steps=3), inventory_dir=tmp_path / "inv",
                           semantic_registry_dir=tmp_path / "sem")
    try:
        env.reset()
        original = env._plant.backend.solve_snapshot

        def injected_failure():
            raise RuntimeError("INJECTED_BACKEND_FAILURE")

        env._plant.backend.solve_snapshot = injected_failure
        with pytest.raises(RuntimeError, match="INJECTED_BACKEND_FAILURE"):
            env.step({})
        assert len(env.history) == 1
        with pytest.raises(RuntimeError, match="reset"):
            env.step({})
        env._plant.backend.solve_snapshot = original
        obs, info = env.reset()
        assert env.observation_space.contains(obs)
        assert info["solution"]["converged"] is True
    finally:
        env.close()
