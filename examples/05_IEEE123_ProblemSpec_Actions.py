"""EXAMPLE 05 - ProblemSpec: authorize and apply a physical PV Q command.

PREAMBLE
========
Aim
    Demonstrate the three separate layers of a controlled environment:
    (1) observation requests, (2) authorized action requests, and
    (3) control authority over specific native equipment.

What you will learn
    - Compose an explicit ObservationSpec and ActionSpec.
    - Understand ActionRestriction, intrinsic device limits, and Gym shapes.
    - Delegate *one* PVSystem to EXTERNAL authority; other feeder equipment
      continues under its own established/native control mechanisms.
    - Supply a complete nested Gym action and inspect physical action audits.
    - Distinguish the requested command from the realized device readback.

This is NOT an RBC or MPC implementation: the learning action is a fixed 0 kvar
setpoint. The P1 controller lessons will replace this with controller(state,
forecast) while keeping exactly this simulator and Gym action interface.

Input
    Input/IEEE123_P1/IEEE123Master.dss (canonical IEEE-123 plus 10 PVs).
Output
    Output/05_one_pv_action/ when SAVE_RESULTS=True.
"""

# =============================================================================
# SECTION 1 - IMPORTS
# =============================================================================
import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from opendsssim.environment import EpisodeSpec, OpenDSSSimulator
from opendsssim.problem import (
    ActionRestriction, ActionSpec, ControlAuthorityMode, ControlAuthoritySpec,
    ObservationSpec, ProblemSpec, RegistryKind, SelectionGroup, SemanticQuery,
)


# =============================================================================
# SECTION 2 - USER SETTINGS
# =============================================================================
HERE = Path(__file__).resolve().parent
CIRCUIT = HERE / "Input" / "IEEE123_P1" / "IEEE123Master.dss"
OUTPUT = HERE / "Output"
RUN_NAME = "05_one_pv_action"
STEPS = 3
SAVE_RESULTS = True
PRINT_FULL_ACTION_LAYOUT = True
RESET_SEED = 1
PV_ENTITY = "PVSystem.PVD47"
PV_Q_SETPOINT_KVAR = 0.0           # Conservative demonstration, not optimization
PV_Q_STUDY_BOUND_KVAR = 25.0      # Additional educational limit (native bound is wider)


# =============================================================================
# SECTION 3 - AUTHOR THE PROBLEM CONTRACT
# =============================================================================
# SemanticQuery asks the existing A03 semantic registry for native quantities.
# It does not create a new physical property or introduce new native controls.
# ActionSpec declares exactly ONE permitted command. All other physical
# devices are deliberately absent from the external Gym action space.
problem = ProblemSpec.create(
    problem_id="tutorial-ieee123-single-pv-action",
    problem_version="1",
    observations=ObservationSpec(groups=(
        SelectionGroup("voltages", (SemanticQuery(
            RegistryKind.STATE, dss_class="Bus", quantity="bus_voltage_pu"
        ),)),
        SelectionGroup("convergence", (SemanticQuery(
            RegistryKind.STATE, quantity="solution_converged"
        ),)),
    )),
    actions=ActionSpec(groups=(
        SelectionGroup(
            group_id="pv_q_control",
            selections=(SemanticQuery(
                RegistryKind.ACTION,
                native_entity=PV_ENTITY,
                quantity="pv_reactive_power_command",
            ),),
            # These study limits cannot relax native PV equipment bounds.
            action_restriction=ActionRestriction(
                low=-PV_Q_STUDY_BOUND_KVAR,
                high=PV_Q_STUDY_BOUND_KVAR,
            ),
        ),
    )),
    control_authority=ControlAuthoritySpec(
        mode=ControlAuthorityMode.EXTERNAL,
        external_entities=(PV_ENTITY,),
    ),
    metadata={"course_example": 5, "purpose": "single-authorized-action"},
)


# =============================================================================
# SECTION 4 - CREATE SIMULATOR / PERSISTENCE DIRECTORIES
# =============================================================================
if not CIRCUIT.is_file():
    raise FileNotFoundError(CIRCUIT)
if STEPS < 1:
    raise ValueError("STEPS must be >= 1")
if abs(PV_Q_SETPOINT_KVAR) > PV_Q_STUDY_BOUND_KVAR:
    raise ValueError("Requested PV Q setpoint exceeds authored study bound")

with TemporaryDirectory(prefix="opendsssim_e05_") as temporary:
    run = OUTPUT / RUN_NAME if SAVE_RESULTS else Path(temporary)
    if SAVE_RESULTS and run.exists():
        raise FileExistsError(f"Choose a new RUN_NAME; output exists: {run}")
    run.mkdir(parents=True, exist_ok=True)
    env = OpenDSSSimulator(
        network=CIRCUIT,
        backend="altdss",
        problem=problem,
        episode_spec=EpisodeSpec(
            start_time_utc="2026-01-01T00:00:00Z", dt_seconds=3600,
            max_steps=STEPS,
        ),
        history_level="H1",
        inventory_dir=run / "Inventory",
        semantic_registry_dir=run / "SemanticRegistry",
        preflight_dir=run / "Preflight",
    )

    try:
        # =====================================================================
        # SECTION 5 - RESET AND INSPECT EXACT ACTION AUTHORITY
        # =====================================================================
        observation, info = env.reset(seed=RESET_SEED)
        print("\nEXAMPLE 05 - ONE AUTHORIZED PV REACTIVE POWER ACTION")
        print("Circuit:", CIRCUIT.name)
        print("Gym observation space:", env.observation_space)
        print("Gym action space:", env.action_space)
        print("Problem SHA256:", problem.problem_spec_sha256)
        print("Preflight:", env.preflight_status)
        context = env.controller_context(
            device_entities=(PV_ENTITY,), include_static_network=False
        )
        print("Authorized action channels:", len(context.action_layout))
        for device in context.devices:
            print("Device:", device.native_entity, "commandability:", device.commandability,
                  "enabled:", device.enabled)
        if PRINT_FULL_ACTION_LAYOUT:
            for item in context.action_layout:
                print("Compiled action layout:", item)
        if len(context.action_layout) != 1:
            raise RuntimeError("Expected exactly one compiled PV action channel")

        # The canonical Gym action path uses the original native class/name:
        # {'PVSystem': {'PVD47': {'pv_reactive_power_command': scalar_Box}}}
        # np.asarray(..., dtype=float64) is important: Box requires a specific
        # numeric type/shape. We do not send backend commands or DSS text.
        action = {
            "PVSystem": {
                "PVD47": {
                    "pv_reactive_power_command": np.asarray(
                        PV_Q_SETPOINT_KVAR, dtype=np.float64
                    )
                }
            }
        }
        if not env.action_space.contains(action):
            raise RuntimeError("Action is not legal under the compiled Gym space")

        # =====================================================================
        # SECTION 6 - CLOSED LOOP: user explicitly owns the env.step() call
        # =====================================================================
        rows = []
        audits = []
        for step in range(1, STEPS + 1):
            # No controller function yet; the constant command is pedagogical.
            observation, reward, terminated, truncated, info = env.step(action)
            if not env.observation_space.contains(observation):
                raise RuntimeError("Observation does not match compiled space")
            step_audits = info["action_audit"]
            if len(step_audits) != 1:
                raise RuntimeError("Expected one audit entry for the one PV action")
            audit = step_audits[0]
            rows.append({
                "step": step,
                "time_utc": info["time"]["electrical_sample_time_utc"],
                "ac_converged": bool(info["solution"]["converged"]),
                "requested_kvar": PV_Q_SETPOINT_KVAR,
                "action_status": audit["status"],
                "total_power_kw": info["solution"]["total_power_kw"],
                "total_power_kvar": info["solution"]["total_power_kvar"],
            })
            audits.append({"step": step, "action_audit": step_audits})
            print(f"Step {step:02d} | AC={rows[-1]['ac_converged']} | "
                  f"request={PV_Q_SETPOINT_KVAR:.1f} kvar | "
                  f"action={audit['status']} | "
                  f"realized={audit.get('realized_value')}")
            # Important: action application and *realized* readbacks may differ.
            if terminated or truncated:
                break

        # =====================================================================
        # SECTION 7 - SAVE CSV / JSON (OPTIONAL)
        # =====================================================================
        if SAVE_RESULTS:
            with (run / "pv_action_steps.csv").open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)

            def save(name, obj):
                (run / name).write_text(json.dumps(
                    obj, indent=2, default=lambda x:
                    x.tolist() if hasattr(x, "tolist") else str(x)) + "\n", encoding="utf-8")

            save("problem_spec.json", problem.semantic_dict())
            save("controller_context_reset.json", context.to_dict())
            save("compiled_action_layout.json", context.to_dict()["action_layout"])
            save("action_readbacks.json", audits)
            save("history.json", env.history.records)
            print("Saved to:", run)
        else:
            print("SAVE_RESULTS=False: no permanent outputs")
    finally:
        # =====================================================================
        # SECTION 8 - CLEAN UP
        # =====================================================================
        env.close()
