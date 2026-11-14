from __future__ import annotations

from pathlib import Path
import numpy as np
import pytest

from opendsssim.environment.simulator import OpenDSSSimulator
from opendsssim.problem import (
    ActionSpec, ControlAuthorityMode, ControlAuthoritySpec, DeviceRef, FaultSpec,
    ObservationSpec, ProblemSpec, RegistryKind, SelectionGroup, SemanticQuery,
    compile_gym_spaces, resolve_problem,
)
from opendsssim.runtime import SemanticRuntimeAccess, build_runtime_binding
from opendsssim.runtime.binding import RuntimeBindingError
from opendsssim.semantics.schema import NativePropertyAddress

FIXTURE = Path(__file__).parents[1] / "fixtures" / "a03_semantic" / "Master.dss"


def transformer_problem(*, hybrid: bool = False):
    authority = ControlAuthoritySpec(
        ControlAuthorityMode.HYBRID if hybrid else ControlAuthorityMode.EXTERNAL,
        native_entities=("Capacitor.Cap1",) if hybrid else (),
        external_entities=("Transformer.RegX",),
    )
    return ProblemSpec.create(
        "a04i3-transformer-authority", f"h{int(hybrid)}",
        observations=ObservationSpec(groups=(SelectionGroup("obs", (SemanticQuery(RegistryKind.STATE, quantity="solution_converged"),)),)),
        actions=ActionSpec(groups=(SelectionGroup("tap", (SemanticQuery(RegistryKind.ACTION, native_entity="Transformer.RegX", quantity="transformer_tap_command"),)),)),
        control_authority=authority,
    )


def pv_fault_problem():
    return ProblemSpec.create(
        "a04i3-pv-fault", "1",
        observations=ObservationSpec(groups=(SelectionGroup("obs", (SemanticQuery(RegistryKind.STATE, quantity="solution_converged"),)),)),
        actions=ActionSpec(groups=(SelectionGroup("pv", (SemanticQuery(RegistryKind.ACTION, native_entity="PVSystem.PV1", quantity="pv_reactive_power_command"),)),)),
        control_authority=ControlAuthoritySpec(
            ControlAuthorityMode.EXTERNAL, external_entities=("PVSystem.PV1",)
        ),
        faults=(FaultSpec("pv_fault", (DeviceRef("PVSystem.PV1"),)),),
    )


def switch_external_problem():
    return ProblemSpec.create(
        "a04i3-switch-role-compatibility", "1",
        observations=ObservationSpec(groups=(SelectionGroup("obs", (SemanticQuery(RegistryKind.STATE, quantity="solution_converged"),)),)),
        actions=ActionSpec(groups=(SelectionGroup("switch", (SemanticQuery(RegistryKind.ACTION, native_entity="Line.Feeder", quantity="branch_switch_command"),)),)),
        control_authority=ControlAuthoritySpec(
            ControlAuthorityMode.EXTERNAL, external_entities=("Line.Feeder",)
        ),
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


def test_a04i3_hybrid_disables_only_controlling_external_native_controller(tmp_path: Path):
    env = OpenDSSSimulator(
        FIXTURE, problem=transformer_problem(hybrid=True),
        inventory_dir=tmp_path/"inv", semantic_registry_dir=tmp_path/"sem", preflight_dir=tmp_path/"pre",
    )
    try:
        env.reset()
        access = SemanticRuntimeAccess(env._plant.backend)
        assert bool(access.read(NativePropertyAddress("RegControl.RC1", "Enabled"))) is False
        assert bool(access.read(NativePropertyAddress("CapControl.CC1", "Enabled"))) is True
    finally:
        env.close()


def test_a04i3_switches_relationship_is_explicitly_verified_by_successor(tmp_path: Path):
    env = OpenDSSSimulator(
        FIXTURE, problem=switch_external_problem(),
        inventory_dir=tmp_path / "inv", semantic_registry_dir=tmp_path / "sem",
        preflight_dir=tmp_path / "pre",
    )
    try:
        assert env.runtime_binding is not None
        assert tuple(name.casefold() for name in env.runtime_binding.disabled_native_controls) == (
            "swtcontrol.sc1",
        )
        env.reset()
        access = SemanticRuntimeAccess(env._plant.backend)
        assert access.read(NativePropertyAddress("SwtControl.SC1", "Enabled")) is False
    finally:
        env.close()


def test_a04i3_fault_lockout_preserves_action_shape_but_does_not_apply(tmp_path: Path):
    env = OpenDSSSimulator(
        FIXTURE, problem=pv_fault_problem(),
        inventory_dir=tmp_path/"inv", semantic_registry_dir=tmp_path/"sem", preflight_dir=tmp_path/"pre",
    )
    try:
        env.reset()
        access = SemanticRuntimeAccess(env._plant.backend)
        assert bool(access.read(NativePropertyAddress("PVSystem.PV1", "Enabled"))) is False
        action = _canonical_action(
            env, "pv_reactive_power_command", np.array(5.0, dtype=np.float64)
        )
        _, _, _, _, info = env.step(action)
        assert info["action_audit"][0]["status"] == "FAULT_DISABLED"
        assert bool(access.read(NativePropertyAddress("PVSystem.PV1", "Enabled"))) is False
    finally:
        env.close()
