from __future__ import annotations

from pathlib import Path
import numpy as np
import pytest

from opendsssim.environment.simulator import OpenDSSSimulator
from opendsssim.problem import (
    ActionSpec, ControlAuthorityMode, ControlAuthoritySpec, ObservationSpec,
    ProblemSpec, RegistryKind, SelectionGroup, SemanticQuery,
)
from opendsssim.semantics.schema import NativePropertyAddress
from opendsssim.runtime import HistoryLevel, SemanticRuntimeAccess

FIXTURE = Path(__file__).parents[1] / "fixtures" / "a03_semantic" / "Master.dss"


def transformer_problem():
    return ProblemSpec.create(
        "a04i3-transformer", "1",
        observations=ObservationSpec(groups=(SelectionGroup("obs", (
            SemanticQuery(RegistryKind.STATE, dss_class="Bus", object_name="source", quantity="bus_voltage_pu"),
            SemanticQuery(RegistryKind.STATE, dss_class="Solution", object_name="__service__", quantity="solution_converged"),
        )),)),
        actions=ActionSpec(groups=(SelectionGroup("tap", (
            SemanticQuery(RegistryKind.ACTION, native_entity="Transformer.RegX", quantity="transformer_tap_command"),
        )),)),
        control_authority=ControlAuthoritySpec(ControlAuthorityMode.EXTERNAL, external_entities=("Transformer.RegX",)),
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
    return action, binding.path


def _nested_get(mapping, path):
    value = mapping
    for part in path:
        value = value[part]
    return value


def test_a04i3_external_authority_one_time_reset_and_persistent_step_context(tmp_path: Path):
    env = OpenDSSSimulator(FIXTURE, problem=transformer_problem(), inventory_dir=tmp_path/"inv", semantic_registry_dir=tmp_path/"sem", preflight_dir=tmp_path/"pre", history_level=HistoryLevel.H3)
    try:
        ctx_id = env.context_identity
        assert env.preflight_status == "BUILT"
        obs, info = env.reset()
        assert env.observation_space.contains(obs)
        assert info["runtime"]["runtime_binding_sha256"] == env.runtime_binding.runtime_binding_sha256
        access = SemanticRuntimeAccess(env._plant.backend)
        assert bool(access.read(NativePropertyAddress("RegControl.RC1", "Enabled"))) is False

        action, action_path = _canonical_action(
            env, "transformer_tap_command", np.array(1.025, dtype=np.float64)
        )
        obs2, reward, terminated, truncated, info2 = env.step(action)
        assert env.context_identity == ctx_id
        assert env.observation_space.contains(obs2)
        assert reward == 0.0 and terminated is False and truncated is False
        assert info2["action_audit"][0]["status"] == "ADMISSIBLE_APPLIED"
        realized = info2["action_audit"][0]["realized_value"]
        assert realized is not None
        assert realized[1] == pytest.approx(1.025)
        assert _nested_get(env.history[1]["realized_action"], action_path)[1] == pytest.approx(1.025)
        assert len(env.history) == 2
        assert env.history[1]["full_state"]

        # Explicit reset recompiles baseline in the same owned backend context and reapplies authority.
        env.reset()
        assert env.context_identity == ctx_id
        assert bool(access.read(NativePropertyAddress("RegControl.RC1", "Enabled"))) is False
    finally:
        env.close()
