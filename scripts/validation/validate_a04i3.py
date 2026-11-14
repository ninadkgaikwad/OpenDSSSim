"""Standalone A04I3 runtime-binding/environment/history/preflight qualification."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import numpy as np

from opendsssim import A04I3_PATCH_ID, __version__
from opendsssim.environment.simulator import OpenDSSSimulator
from opendsssim.problem import (
    ActionSpec,
    ControlAuthorityMode,
    ControlAuthoritySpec,
    DeviceRef,
    FaultSpec,
    ObservationSpec,
    ProblemSpec,
    RegistryKind,
    SelectionGroup,
    SemanticQuery,
    compile_gym_spaces,
    resolve_problem,
)
from opendsssim.runtime import HistoryLevel, SemanticRuntimeAccess, build_runtime_binding
from opendsssim.runtime.binding import RuntimeBindingError
from opendsssim.semantics.schema import NativePropertyAddress

EXPECTED_PATCH_ID = "OpenDSSSim_A04I3_RuntimeBinding_Environment_History_Preflight_v01R3_20261021"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _transformer_problem() -> ProblemSpec:
    return ProblemSpec.create(
        "a04i3-validator-transformer",
        "1",
        observations=ObservationSpec(
            groups=(
                SelectionGroup(
                    "obs",
                    (
                        SemanticQuery(
                            RegistryKind.STATE,
                            dss_class="Bus",
                            object_name="source",
                            quantity="bus_voltage_pu",
                        ),
                        SemanticQuery(
                            RegistryKind.STATE,
                            dss_class="Solution",
                            object_name="__service__",
                            quantity="solution_converged",
                        ),
                    ),
                ),
            )
        ),
        actions=ActionSpec(
            groups=(
                SelectionGroup(
                    "tap",
                    (
                        SemanticQuery(
                            RegistryKind.ACTION,
                            native_entity="Transformer.RegX",
                            quantity="transformer_tap_command",
                        ),
                    ),
                ),
            )
        ),
        control_authority=ControlAuthoritySpec(
            ControlAuthorityMode.EXTERNAL,
            external_entities=("Transformer.RegX",),
        ),
    )


def _pv_fault_problem() -> ProblemSpec:
    return ProblemSpec.create(
        "a04i3-validator-pv-fault",
        "1",
        observations=ObservationSpec(
            groups=(SelectionGroup("obs", (SemanticQuery(RegistryKind.STATE, quantity="solution_converged"),)),)
        ),
        actions=ActionSpec(
            groups=(SelectionGroup("pv", (SemanticQuery(RegistryKind.ACTION, native_entity="PVSystem.PV1", quantity="pv_reactive_power_command"),)),)
        ),
        control_authority=ControlAuthoritySpec(
            ControlAuthorityMode.EXTERNAL, external_entities=("PVSystem.PV1",)
        ),
        faults=(FaultSpec("pv_fault", (DeviceRef("PVSystem.PV1"),)),),
    )


def _switch_external_problem() -> ProblemSpec:
    return ProblemSpec.create(
        "a04i3-validator-switch-role",
        "1",
        observations=ObservationSpec(
            groups=(SelectionGroup("obs", (SemanticQuery(RegistryKind.STATE, quantity="solution_converged"),)),)
        ),
        actions=ActionSpec(
            groups=(SelectionGroup("switch", (SemanticQuery(RegistryKind.ACTION, native_entity="Line.Feeder", quantity="branch_switch_command"),)),)
        ),
        control_authority=ControlAuthoritySpec(
            ControlAuthorityMode.EXTERNAL, external_entities=("Line.Feeder",)
        ),
    )


def _canonical_action(env: OpenDSSSimulator, quantity: str, value: Any) -> dict[str, Any]:
    _require(env.runtime_binding is not None, "Runtime binding missing while constructing canonical action.")
    binding = next(item for item in env.runtime_binding.action_bindings if item.entry.quantity == quantity)
    action: dict[str, Any] = {}
    node = action
    for part in binding.path[:-1]:
        node = node.setdefault(part, {})
    node[binding.path[-1]] = value
    _require(env.action_space.contains(action), f"Canonical action failed Gym contains(): {binding.path}")
    return action


def qualify(repo_root: Path, work_root: Path) -> dict[str, Any]:
    fixture = repo_root / "tests" / "fixtures" / "a03_semantic" / "Master.dss"
    work_root.mkdir(parents=True, exist_ok=True)
    gates: dict[str, bool] = {}

    gates["patch_id"] = A04I3_PATCH_ID == EXPECTED_PATCH_ID
    gates["package_version"] = __version__ == "0.1.0a6"

    shared = {
        "inventory_dir": work_root / "inventory",
        "semantic_registry_dir": work_root / "semantic_registry",
        "preflight_dir": work_root / "preflight",
    }

    env = OpenDSSSimulator(
        fixture,
        problem=_transformer_problem(),
        history_level=HistoryLevel.H3,
        **shared,
    )
    try:
        context_id = env.context_identity
        _require(env.preflight_status == "BUILT", "Initial preflight was not BUILT.")
        _require(env.preflight_path is not None and env.preflight_path.exists(), "Preflight record missing.")
        preflight_payload = json.loads(env.preflight_path.read_text(encoding="utf-8"))
        _require(preflight_payload["opendsssim_version"] == "0.1.0a6", "Source-layout package version was not recorded in preflight.")
        gates["preflight_built"] = True
        gates["preflight_source_version"] = True

        obs, info = env.reset()
        _require(env.observation_space.contains(obs), "Initial canonical observation failed Gym contains().")
        _require(env.runtime_binding is not None, "Runtime binding missing.")
        _require(
            info["runtime"]["runtime_binding_sha256"] == env.runtime_binding.runtime_binding_sha256,
            "Runtime binding identity mismatch in info.",
        )
        gates["runtime_binding"] = True

        access = SemanticRuntimeAccess(env._plant.backend)
        _require(
            bool(access.read(NativePropertyAddress("RegControl.RC1", "Enabled"))) is False,
            "EXTERNAL authority did not suppress RegControl.RC1.",
        )
        gates["external_authority"] = True

        action = _canonical_action(
            env, "transformer_tap_command", np.array(1.025, dtype=np.float64)
        )
        obs2, reward, terminated, truncated, info2 = env.step(action)
        _require(env.observation_space.contains(obs2), "Post-step observation failed Gym contains().")
        _require(reward == 0.0 and not terminated and not truncated, "Default hooks changed neutral behavior.")
        _require(info2["action_audit"][0]["status"] == "ADMISSIBLE_APPLIED", "External action did not apply.")
        realized = info2["action_audit"][0]["realized_value"]
        _require(realized is not None and abs(float(realized[1]) - 1.025) < 1e-12, "Post-solve realized tap state was not audited.")
        gates["realized_action_audit"] = True
        _require(env.context_identity == context_id, "Iterative step changed AltDSS context identity.")
        _require(len(env.history) == 2, "Expected reset + one step in history.")
        _require("full_state" in env.history[1], "H3 history did not retain full_state.")
        gates["persistent_live_context"] = True
        gates["default_hooks"] = True
        gates["history_h3"] = True

        env.reset()
        _require(env.context_identity == context_id, "Explicit reset replaced the owned AltDSS context.")
        _require(
            bool(access.read(NativePropertyAddress("RegControl.RC1", "Enabled"))) is False,
            "Authority was not reapplied after explicit reset.",
        )
        gates["reset_reinitialization"] = True
    finally:
        env.close()

    env2 = OpenDSSSimulator(fixture, problem=_transformer_problem(), **shared)
    try:
        _require(env2.preflight_status == "REUSED", "Identical runtime boundary did not reuse preflight.")
        gates["preflight_reuse"] = True
    finally:
        env2.close()

    # Controlled A04I4A successor: SWITCHES only confers external authority
    # when A02H1 proves a unique suppressible SwtControl and line terminal.
    switch_env = OpenDSSSimulator(
        fixture, problem=_switch_external_problem(),
        inventory_dir=work_root / "switch_inventory",
        semantic_registry_dir=work_root / "switch_semantic_registry",
        preflight_dir=work_root / "switch_preflight",
    )
    try:
        _require(switch_env.runtime_binding is not None, "Switch runtime binding absent.")
        _require(
            tuple(name.casefold() for name in switch_env.runtime_binding.disabled_native_controls)
            == ("swtcontrol.sc1",),
            "Verified SwtControl was not assigned exclusively to external switching.",
        )
        switch_env.reset()
        access = SemanticRuntimeAccess(switch_env._plant.backend)
        _require(
            access.read(NativePropertyAddress("SwtControl.SC1", "Enabled")) is False,
            "External authority did not disable SwtControl.",
        )
        gates["switches_role_verified_successor"] = True
    finally:
        switch_env.close()

    fault_env = OpenDSSSimulator(
        fixture,
        problem=_pv_fault_problem(),
        inventory_dir=work_root / "fault_inventory",
        semantic_registry_dir=work_root / "fault_semantic_registry",
        preflight_dir=work_root / "fault_preflight",
    )
    try:
        fault_env.reset()
        access = SemanticRuntimeAccess(fault_env._plant.backend)
        _require(
            bool(access.read(NativePropertyAddress("PVSystem.PV1", "Enabled"))) is False,
            "Static fault did not force Enabled=False.",
        )
        action = _canonical_action(
            fault_env, "pv_reactive_power_command", np.array(5.0, dtype=np.float64)
        )
        _, _, _, _, info = fault_env.step(action)
        _require(info["action_audit"][0]["status"] == "FAULT_DISABLED", "Faulted action was not locked out.")
        _require(
            bool(access.read(NativePropertyAddress("PVSystem.PV1", "Enabled"))) is False,
            "Faulted device was re-enabled during step.",
        )
        gates["fault_lockout"] = True
    finally:
        fault_env.close()

    failed = [name for name, passed in gates.items() if not passed]
    return {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "patch_id": EXPECTED_PATCH_ID,
        "repo_root": str(repo_root),
        "gates": gates,
        "failed_gates": failed,
        "status": "PASS" if not failed else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = qualify(args.repo_root.resolve(), args.work_root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(f"REPORT={args.output}")
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["status"] == "PASS":
        print("A04I3 STANDALONE VALIDATOR: PASS")
        return 0
    print("A04I3 STANDALONE VALIDATOR: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
