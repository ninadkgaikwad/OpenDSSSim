from __future__ import annotations

from pathlib import Path
import numpy as np
import pytest

from opendsssim.environment.simulator import OpenDSSSimulator, RuntimeHookError
from opendsssim.problem import (
    ActionSpec, ControlAuthorityMode, ControlAuthoritySpec, HookSpec, ObservationSpec,
    ProblemSpec, RegistryKind, SelectionGroup, SemanticQuery,
)

FIXTURE = Path(__file__).parents[1] / "fixtures" / "a03_semantic" / "Master.dss"



def _problem(reward_name="configured_reward"):
    return ProblemSpec.create(
        "a04i3-hooks", reward_name,
        observations=ObservationSpec(groups=(SelectionGroup("obs", (SemanticQuery(RegistryKind.STATE, quantity="solution_converged"),)),)),
        actions=ActionSpec(groups=(SelectionGroup("pv", (SemanticQuery(RegistryKind.ACTION, native_entity="PVSystem.PV1", quantity="pv_reactive_power_command"),)),)),
        control_authority=ControlAuthoritySpec(ControlAuthorityMode.EXTERNAL, external_entities=("PVSystem.PV1",)),
        reward=HookSpec.imported("tests.a04i3_hooks", reward_name, config={"scale": 2.0}) if reward_name == "configured_reward" else HookSpec.imported("tests.a04i3_hooks", reward_name),
        termination=HookSpec.imported("tests.a04i3_hooks", "terminate_after_one"),
        truncation=HookSpec.imported("tests.a04i3_hooks", "never_truncate"),
    )


def _canonical_action(env: OpenDSSSimulator, quantity: str, value):
    assert env.runtime_binding is not None
    binding = next(item for item in env.runtime_binding.action_bindings if item.entry.quantity == quantity)
    action = {}
    node = action
    for part in binding.path[:-1]:
        node = node.setdefault(part, {})
    node[binding.path[-1]] = value
    assert env.action_space.contains(action)
    return action


def test_a04i3_custom_problem_hooks_receive_runtime_context(tmp_path: Path):
    env = OpenDSSSimulator(FIXTURE, problem=_problem(), inventory_dir=tmp_path/"inv", semantic_registry_dir=tmp_path/"sem", preflight_dir=tmp_path/"pre")
    try:
        env.reset()
        action = _canonical_action(
            env, "pv_reactive_power_command", np.array(5.0, dtype=np.float64)
        )
        _, reward, terminated, truncated, _ = env.step(action)
        assert reward == pytest.approx(2.0)
        assert terminated is True
        assert truncated is False
    finally:
        env.close()


def test_a04i3_invalid_hook_result_fails_without_default_fallback(tmp_path: Path):
    env = OpenDSSSimulator(FIXTURE, problem=_problem("invalid_reward"), inventory_dir=tmp_path/"inv", semantic_registry_dir=tmp_path/"sem", preflight_dir=tmp_path/"pre")
    try:
        env.reset()
        action = _canonical_action(
            env, "pv_reactive_power_command", np.array(5.0, dtype=np.float64)
        )
        with pytest.raises(RuntimeHookError, match="finite scalar"):
            env.step(action)
    finally:
        env.close()
