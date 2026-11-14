"""EXAMPLE 06 - Read-only ControllerContext and exogenous forecasts.

PREAMBLE
========
Aim
    Show what a future P1 RBC/MPC controller is *allowed* to know before
    requesting a physical action: the committed observation, exact action
    layout, device readiness, static network and qualified input forecast.

What you will learn
    - Connect a 24-hour CSV to 91 load devices through ReplaySpec.
    - Understand data ownership: replay = physical truth; forecast = a
      read-only view of explicitly declared exogenous input (NOT future AC).
    - Request ControllerContext(forecast_horizon=H) before each env.step().
    - Read observation, device status, action layout and last action feedback.
    - Apply the same legal 0 kvar PV action demonstrated in Example 05.

This is deliberately NOT a controller. The next lessons will replace the
constant action with an existing controller(state, forecasts) function.

Input
    Input/IEEE123_P1/IEEE123Master.dss
    Input/synthetic_hourly_load_multiplier.csv
    Input/ieee123_load_targets.csv
Output
    Output/06_controller_information/ when SAVE_RESULTS=True.

Scientific note
    Forecasts are zero-error exogenous *oracle* data in this example. They
    are not inferred from future realized electrical state, and this is not
    a claim of realistic predictive forecast accuracy.
"""

# =============================================================================
# SECTION 1 - IMPORTS
# =============================================================================
import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from opendsssim.environment import (
    OpenDSSSimulator, ReplayBinding, ReplaySource, ReplaySpec,
)
from opendsssim.problem import (
    ActionRestriction, ActionSpec, ControlAuthorityMode, ControlAuthoritySpec,
    ObservationSpec, ProblemSpec, RegistryKind, SelectionGroup, SemanticQuery,
)


# =============================================================================
# SECTION 2 - USER SETTINGS: try HORIZON=1 or STEPS=4
# =============================================================================
HERE = Path(__file__).resolve().parent
INPUT = HERE / "Input"
OUTPUT = HERE / "Output"
CIRCUIT = INPUT / "IEEE123_P1" / "IEEE123Master.dss"
LOAD_PROFILE = INPUT / "synthetic_hourly_load_multiplier.csv"
LOAD_TARGETS = INPUT / "ieee123_load_targets.csv"
RUN_NAME = "06_controller_information"
STEPS = 3
FORECAST_HORIZON = 2
SAVE_RESULTS = True
PRINT_EACH_FORECAST = False
PV_ENTITY = "PVSystem.PVD47"
PV_Q_SETPOINT_KVAR = 0.0


# =============================================================================
# SECTION 3 - READ THE PHYSICAL TIME-SERIES INPUT FILES
# =============================================================================
for file in (CIRCUIT, LOAD_PROFILE, LOAD_TARGETS):
    if not file.is_file():
        raise FileNotFoundError(file)
with LOAD_PROFILE.open(newline="", encoding="utf-8") as f:
    available_samples = sum(1 for _ in csv.DictReader(f))
if STEPS < 1 or FORECAST_HORIZON < 1 or (STEPS + FORECAST_HORIZON - 1) > available_samples:
    raise ValueError("STEPS/FORECAST_HORIZON exceed available replay coverage")

with LOAD_TARGETS.open(newline="", encoding="utf-8") as f:
    targets = tuple(row["native_load"] for row in csv.DictReader(f))
if len(targets) != 91 or len(set(x.casefold() for x in targets)) != len(targets):
    raise ValueError("Expected 91 unique IEEE-123 load identities")

# ReplaySpec owns the time grid. Do not also specify EpisodeSpec.
# Each time sample multiplies every load's original kW and kvar by the CSV
# load_multiplier_pu value. The feeder/PV models are otherwise unchanged.
replay = ReplaySpec(
    sources=(ReplaySource(
        source_id="hourly_load",
        timestamp_column="time_utc",
        timezone_name="UTC",
        path=LOAD_PROFILE,
    ),),
    bindings=(ReplayBinding(
        source_id="hourly_load",
        kind="load",
        targets=targets,
        mode="multiplier",
        columns=("load_multiplier_pu",),
        units=("pu",),
    ),),
    mode="strict",
    dt_seconds=3600,
    start_time_utc="2026-01-01T00:00:00Z",
    max_steps=STEPS,
)


# =============================================================================
# SECTION 4 - DEFINE WHAT THE CONTROLLER MAY OBSERVE AND COMMAND
# =============================================================================
# Only the declared quantity/action pair is authorized. This mirrors Example
# 05 and makes the ControllerContext inspectable. All other candidate action
# channels are absent; future RBC/MPC examples will declare more channels.
problem = ProblemSpec.create(
    problem_id="tutorial-ieee123-forecast-context",
    problem_version="1",
    observations=ObservationSpec(groups=(
        SelectionGroup("voltages", (SemanticQuery(
            RegistryKind.STATE, dss_class="Bus", quantity="bus_voltage_pu"
        ),)),
        SelectionGroup("convergence", (SemanticQuery(
            RegistryKind.STATE, quantity="solution_converged"
        ),)),
    )),
    actions=ActionSpec(groups=(SelectionGroup(
        "one_pv_command",
        (SemanticQuery(RegistryKind.ACTION, native_entity=PV_ENTITY,
                       quantity="pv_reactive_power_command"),),
        action_restriction=ActionRestriction(low=-25.0, high=25.0),
    ),)),
    control_authority=ControlAuthoritySpec(
        ControlAuthorityMode.EXTERNAL, external_entities=(PV_ENTITY,),
    ),
    metadata={"course_example": 6, "purpose": "controller-information"},
)


# =============================================================================
# SECTION 5 - CONSTRUCT/RESET THE REAL SIMULATOR
# =============================================================================
with TemporaryDirectory(prefix="opendsssim_e06_") as temporary:
    run = OUTPUT / RUN_NAME if SAVE_RESULTS else Path(temporary)
    if SAVE_RESULTS and run.exists():
        raise FileExistsError(f"Choose new RUN_NAME: {run}")
    run.mkdir(parents=True, exist_ok=True)

    env = OpenDSSSimulator(
        network=CIRCUIT,
        backend="altdss",
        problem=problem,
        exogenous_replay=replay,
        history_level="H1",
        inventory_dir=run / "Inventory",
        semantic_registry_dir=run / "SemanticRegistry",
        preflight_dir=run / "Preflight",
    )

    try:
        observation, info = env.reset(seed=1)
        print("\nEXAMPLE 06 - CONTROLLER INFORMATION & FORECASTS")
        print("Reset AC converged:", info["solution"]["converged"])
        print("Replay physical inputs:", len(targets), "IEEE-123 loads")
        print("Gym action space:", env.action_space)

        # =====================================================================
        # SECTION 6 - AT EACH DECISION TIME, READ *DETACHED* CONTROLLER INPUT
        # =====================================================================
        # IMPORTANT CLOCK SEMANTICS: after reset, completed_steps=0;
        # forecast for decision 0 covers canonical samples 0, 1 (H=2).
        # env.step() then applies the corresponding physical time-series row.
        rows = []
        contexts = []
        for step in range(1, STEPS + 1):
            state = env.controller_context(
                forecast_horizon=FORECAST_HORIZON,
                required=True,                 # fail if any lead is not covered
                device_entities=(PV_ENTITY,),   # live readback only for authorized PV
                include_static_network=(step == 1),
            )
            forecasts = state.forecast
            if forecasts is None or forecasts.status != "AVAILABLE":
                raise RuntimeError("Declared replay forecasts are not available")
            if len(state.action_layout) != 1:
                raise RuntimeError("Expected the one authorized PV action")

            print(f"\nDecision before step {step}: {state.decision_time_utc}")
            print("  Completed steps:", state.completed_steps)
            print("  Forecast horizon:", forecasts.horizon,
                  "| exposed values:", len(forecasts.values))
            print("  Current observation classes:",
                  list(state.observation.get("current", {})))
            print("  Authorized action channels:", len(state.action_layout))
            print("  Device commandability:",
                  [(d.native_entity, d.commandability) for d in state.devices])
            print("  Previous realized feedback:", len(state.last_realized_action_feedback))
            if state.static_network is not None:
                print("  Static network buses:", len(state.static_network.buses),
                      "| elements:", len(state.static_network.elements))
            if PRINT_EACH_FORECAST:
                for item in forecasts.values:
                    print("    lead", item.lead_index, item.entity_id,
                          item.channel_id, item.value, item.unit)
            else:
                print("  First two exogenous forecast values:", [
                    (item.lead_index, item.entity_id, item.value)
                    for item in forecasts.values[:2]
                ])

            # =================================================================
            # SECTION 7 - EXPLICIT STEP: action chosen by user (no controller yet)
            # =================================================================
            action = {"PVSystem": {"PVD47": {
                "pv_reactive_power_command": np.asarray(
                    PV_Q_SETPOINT_KVAR, dtype=np.float64
                )
            }}}
            if not env.action_space.contains(action):
                raise RuntimeError("Invalid Gym action")
            observation, reward, terminated, truncated, info = env.step(action)
            if not env.observation_space.contains(observation):
                raise RuntimeError("Invalid Gym observation")
            print("  AC converged:", info["solution"]["converged"],
                  "| action status:", info["action_audit"][0]["status"])

            rows.append({
                "step": step,
                "decision_time_utc": state.decision_time_utc,
                "electrical_sample_time_utc": info["time"]["electrical_sample_time_utc"],
                "forecast_horizon": forecasts.horizon,
                "forecast_value_count": len(forecasts.values),
                "ac_converged": bool(info["solution"]["converged"]),
                "action_status": info["action_audit"][0]["status"],
            })
            if SAVE_RESULTS:
                contexts.append({"step": step, "controller_context": state.to_dict()})
            if terminated or truncated:
                break

        # =====================================================================
        # SECTION 8 - OPTIONAL OUTPUT (NO BACKEND HANDLES OR FUTURE AC TRUTH)
        # =====================================================================
        if SAVE_RESULTS:
            with (run / "controller_information_steps.csv").open(
                "w", newline="", encoding="utf-8"
            ) as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)

            def save(name, value):
                (run / name).write_text(json.dumps(
                    value, indent=2, default=lambda x:
                    x.tolist() if hasattr(x, "tolist") else str(x)) + "\n", encoding="utf-8")

            save("authored_problem.json", problem.semantic_dict())
            save("controller_context_per_step.json", contexts)
            save("history.json", env.history.records)
            print("Saved to:", run)
        else:
            print("SAVE_RESULTS=False: no permanent outputs")
    finally:
        # =====================================================================
        # SECTION 9 - CLOSE
        # =====================================================================
        env.close()
