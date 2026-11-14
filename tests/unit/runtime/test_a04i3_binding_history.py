from __future__ import annotations

from pathlib import Path

from opendsssim.problem import (
    ActionSpec, ControlAuthorityMode, ControlAuthoritySpec, ObservationSpec,
    ProblemSpec, RegistryKind, SelectionGroup, SemanticQuery,
    compile_gym_spaces, resolve_problem,
)
from opendsssim.runtime import ExecutionProfile, HistoryLevel, RuntimeHistory, RuntimeStepContext
from tests.unit.problem._helpers import make_inventory_and_bundle


def test_a04i3_history_levels_are_independent_of_execution_profile():
    ctx = RuntimeStepContext.create(
        step_index=1, observation={"x": 1}, requested_action={"u": 2}, applied_action={"u": 2},
        realized_action={"u": 2}, action_audit=(), internal_state={"s": 3}, disturbances={"d": 4},
        parameters={"p": 5}, constraints={"c": 6}, availability={"a": True}, authority={"mode": "EXTERNAL"},
        solution={"converged": True},
    )
    h0 = RuntimeHistory(HistoryLevel.H0, ExecutionProfile.AUDIT)
    h0.append(ctx, phase="step", reward=1.0, terminated=False, truncated=False, info={"hidden": 7}, full_state={"all": 8})
    assert "full_state" not in h0[0]
    assert "info" not in h0[0]

    h1 = RuntimeHistory(HistoryLevel.H1, ExecutionProfile.FAST)
    h1.append(ctx, phase="step", reward=1.0, terminated=False, truncated=False, info={"hidden": 7}, full_state={"all": 8})
    assert h1[0]["requested_action"] == {"u": 2}
    assert "full_state" not in h1[0]
    assert "info" not in h1[0]

    h2 = RuntimeHistory(HistoryLevel.H2, ExecutionProfile.STANDARD)
    h2.append(ctx, phase="step", reward=1.0, terminated=False, truncated=False, info={"hidden": 7}, full_state={"all": 8})
    assert h2[0]["full_state"] == {"all": 8}
    assert "info" not in h2[0]

    h3 = RuntimeHistory(HistoryLevel.H3, ExecutionProfile.FAST)
    h3.append(ctx, phase="step", reward=1.0, terminated=False, truncated=False, info={"hidden": 7}, full_state={"all": 8})
    assert h3[0]["full_state"] == {"all": 8}
    assert h3[0]["info"] == {"hidden": 7}


def test_a04i3_problem_contract_can_be_resolved_for_runtime_binding():
    inventory, bundle = make_inventory_and_bundle()
    problem = ProblemSpec.create(
        "runtime-unit", "1",
        observations=ObservationSpec(groups=(SelectionGroup("obs", (SemanticQuery(RegistryKind.STATE, quantity="solution_converged"),)),)),
        actions=ActionSpec(groups=(SelectionGroup("act", (SemanticQuery(RegistryKind.ACTION, native_entity="PVSystem.PV1"),)),)),
        control_authority=ControlAuthoritySpec(ControlAuthorityMode.EXTERNAL, external_entities=("PVSystem.PV1",)),
    )
    resolved = resolve_problem(problem, bundle, inventory)
    compiled = compile_gym_spaces(resolved)
    assert resolved is not None
    assert compiled.resolved_problem_sha256 == resolved.resolved_problem_sha256
