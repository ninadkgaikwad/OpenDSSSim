"""A05I1B real IEEE-123 hook timing, compatibility and fail-closed tests."""
from pathlib import Path

import pytest

from opendsssim.environment import EpisodeSpec, OpenDSSSimulator, TemporalRuntimeStepContext
from opendsssim.environment.simulator import RuntimeHookError
from opendsssim.problem import HookSpec, ObservationSpec, ProblemSpec, RegistryKind, SelectionGroup, SemanticQuery
from opendsssim.runtime import HistoryLevel, RuntimeStepContext


FEEDERS = Path(__file__).resolve().parents[2] / "experiments" / "pesgm2027" / "feeders"


def _time_problem(*, invalid=False):
    return ProblemSpec.create(
        "a05i1b-temporal-hooks", "1",
        observations=ObservationSpec(groups=(
            SelectionGroup("obs", (SemanticQuery(RegistryKind.STATE, quantity="solution_converged"),)),
        )),
        reward=HookSpec.imported("tests.a05i1b_hooks", "illegal_time_mutation" if invalid else "reward_from_time"),
        termination=HookSpec.imported("tests.a05i1b_hooks", "terminate_second_step"),
        truncation=HookSpec.imported("tests.a05i1b_hooks", "never_truncate"),
    )


@pytest.mark.parametrize("feeder", ["ieee123_base", "ieee123_pesgm2027"])
def test_ieee123_hooks_see_current_option_a_clock_without_extra_solve(tmp_path, feeder):
    master = FEEDERS / feeder / "IEEE123Master.dss"
    assert master.is_file(), f"Genuine feeder missing: {master}"
    env = OpenDSSSimulator(
        master, problem=_time_problem(),
        episode_spec=EpisodeSpec(dt_seconds=900, max_steps=3),
        history_level=HistoryLevel.H0,
        inventory_dir=tmp_path / "inv", semantic_registry_dir=tmp_path / "sem",
        preflight_dir=tmp_path / "pre",
    )
    try:
        solver = env._plant.backend.solve_snapshot
        calls = 0

        def counted():
            nonlocal calls
            calls += 1
            return solver()

        env._plant.backend.solve_snapshot = counted
        observation, reset_info = env.reset(seed=19)
        assert env.observation_space.contains(observation)
        assert reset_info["solution"]["converged"] is True
        assert calls == 1
        initial = env.state
        assert isinstance(initial, TemporalRuntimeStepContext)
        assert isinstance(initial, RuntimeStepContext)
        assert dict(initial.time) == reset_info["time"] == env.history[0]["time"]
        assert initial.time["phase"] == "reset"

        _, reward1, term1, trunc1, step1 = env.step({})
        assert step1["solution"]["converged"] is True
        assert calls == 2
        assert (reward1, term1, trunc1) == (1.0, False, False)
        assert step1["time"]["electrical_sample_time_utc"] == reset_info["time"]["electrical_sample_time_utc"]
        assert dict(env.state.time) == step1["time"] == env.history[1]["time"]
        with pytest.raises(TypeError):
            env.state.time["decision_time_utc"] = "MUTATED"

        _, reward2, term2, trunc2, step2 = env.step({})
        assert step2["solution"]["converged"] is True
        assert calls == 3
        assert (reward2, term2, trunc2) == (2.0, True, False)
        assert step2["time"]["electrical_sample_time_utc"] == step1["time"]["decision_time_utc"]
        assert dict(env.state.time) == step2["time"] == env.history[2]["time"]
        with pytest.raises(RuntimeError, match="reset"):
            env.step({})
        assert calls == 3
    finally:
        env.close()


def test_ieee123_illegal_hook_time_write_locks_episode(tmp_path):
    master = FEEDERS / "ieee123_base" / "IEEE123Master.dss"
    env = OpenDSSSimulator(
        master, problem=_time_problem(invalid=True),
        episode_spec=EpisodeSpec(max_steps=3),
        inventory_dir=tmp_path / "inv", semantic_registry_dir=tmp_path / "sem",
        preflight_dir=tmp_path / "pre",
    )
    try:
        env.reset()
        with pytest.raises(RuntimeHookError, match="hook raised") as raised:
            env.step({})
        assert isinstance(raised.value.__cause__, TypeError)
        assert len(env.history) == 1
        with pytest.raises(RuntimeError, match="reset"):
            env.step({})
    finally:
        env.close()


def test_ieee123_no_problem_legacy_context_has_readonly_time(tmp_path):
    master = FEEDERS / "ieee123_base" / "IEEE123Master.dss"
    env = OpenDSSSimulator(
        master, episode_spec=EpisodeSpec(max_steps=1),
        history_level=HistoryLevel.H3,
        inventory_dir=tmp_path / "inv", semantic_registry_dir=tmp_path / "sem",
    )
    try:
        _, info = env.reset()
        assert isinstance(env.state, TemporalRuntimeStepContext)
        assert dict(env.state.time) == info["time"]
        assert env.history[0]["time"] == info["time"]
        _, _, _, truncated, info = env.step({})
        assert truncated
        assert dict(env.state.time) == info["time"]
        assert env.history[1]["time"] == info["time"]
    finally:
        env.close()
