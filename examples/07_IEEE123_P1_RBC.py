"""EXAMPLE 07 - P1 RULE-BASED VOLT/VAR CONTROL (RBC) ON IEEE-123.

PREAMBLE
========
Purpose
    Demonstrate a complete user-owned closed loop with the installed
    P1RuleBasedController: PV reactive power, capacitor states, regulator taps.

Read this script from top to bottom. Sections are intentionally visible:
    1 imports; 2 settings; 3 input/replay; 4 ProblemSpec; 5 env/reset;
    6 RBC configuration; 7 controller(state, forecasts); 8 closed loop;
    9 optional output and close.

Scientific limitations
    - The P1 case supplies *offline equipment/monitor metadata*; RBC does not
      solve the MPC mathematical program.
    - The supplied 48-row constant load replay is an educational experiment.
      PV availability is the fixed, qualified case value (not a solar forecast).
    - The original IEEE-123 regulators/capacitors are not augmented.
    - This tutorial is NOT a claim of exact reproduction of the archived S10C
      RBC research configuration; that archive has its own experiment record.
    - No direct AltDSS/Plant mutation. Actions pass through ProblemSpec + step.

Inputs: examples/Input/IEEE123_P1 and Input/ControllerCases.
Outputs: examples/Output/<RUN_NAME> only when SAVE_RESULTS=True.
"""

# =============================================================================
# SECTION 1 - IMPORTS: these are installed OpenDSSSim public classes/functions
# =============================================================================
import csv
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from opendsssim.environment import OpenDSSSimulator, ReplaySource, ReplayBinding, ReplaySpec
from opendsssim.controllers.reference import (
    make_p1_problem, P1Monitor, P1Spec, P1RuleBasedController,
)
from opendsssim.controllers.mpc.closed_loop_a07a2 import p1_case_from_json


# =============================================================================
# SECTION 2 - USER SETTINGS: edit these first; leave source/controller untouched
# =============================================================================
HERE = Path(__file__).resolve().parent
INPUT = HERE / "Input"
CIRCUIT = INPUT / "IEEE123_P1" / "IEEE123Master.dss"
CASE_FILE = INPUT / "ControllerCases" / "ieee123_pesgm2027_lindist_case.json"
LOAD_PROFILE = INPUT / "ControllerCases" / "constant_hourly_load_multiplier.csv"
LOAD_TARGETS = INPUT / "ieee123_load_targets.csv"
OUTPUT = HERE / "Output"
RUN_NAME = "07_p1_rbc"
STEPS = 3                 # Extend to <= 24 after native validation
SAVE_RESULTS = True       # False = temporary preflight outputs, nothing retained
PRINT_ACTIONS = False     # Print complete nested Gym command dictionaries
PRINT_VOLTAGES = True
RESET_SEED = 511


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def voltage_summary(observation):
    """Read the *authorized observation*, not a native backend voltage handle."""
    values = []
    for bus, entry in observation.get("current", {}).get("Bus", {}).items():
        if "bus_voltage_pu" in entry:
            values.extend(float(v) for v in np.asarray(
                entry["bus_voltage_pu"], dtype=float).reshape(-1)
                if np.isfinite(v) and v > 1e-4)
    return {"vmin_pu": min(values) if values else None,
            "vmax_pu": max(values) if values else None,
            "energized_components": len(values),
            "outside_095_105": sum(v < 0.95 or v > 1.05 for v in values)}


def make_rbc_spec(state, case):
    """Explicitly attach each control device to a monitored bus (public data)."""
    elements = {x.native_entity.casefold(): x for x in state.static_network.elements}
    monitors = {}
    for pv in case.pv:
        monitors[pv.entity] = P1Monitor(bus=pv.locations[0][0])
    for cap in case.capacitors:
        monitors[cap.entity] = P1Monitor(bus=cap.locations[0][0])
    for tap in case.taps:
        device = elements.get(tap.entity.casefold())
        if device is None or not device.terminal_bus_specs:
            raise RuntimeError("Regulator downstream monitor missing: " + tap.entity)
        monitors[tap.entity] = P1Monitor(
            bus=device.terminal_bus_specs[-1].split(".")[0])
    return P1Spec(monitors=monitors,
                  kva={p.entity: p.kva for p in case.pv},
                  tap_step={t.entity: t.step_ratio for t in case.taps},
                  tap_winding_index={t.entity: 1 for t in case.taps})


# =============================================================================
# SECTION 3 - INPUT: explicit ReplaySource -> ReplayBinding -> ReplaySpec
# =============================================================================
for required in (CIRCUIT, CASE_FILE, LOAD_PROFILE, LOAD_TARGETS):
    if not required.is_file():
        raise FileNotFoundError(required)
if not 1 <= STEPS <= 24:
    raise ValueError("This teaching dataset supports 1..24 closed-loop steps")

case = p1_case_from_json(json.loads(CASE_FILE.read_text(encoding="utf-8")))
with LOAD_TARGETS.open(newline="", encoding="utf-8") as f:
    targets = tuple(row["native_load"] for row in csv.DictReader(f))
if len(targets) != 91 or len({x.casefold() for x in targets}) != 91:
    raise ValueError("Expected 91 unique IEEE-123 load targets")

# The physical feeder changes at each declared replay timestamp. This example
# uses a constant 1.0 multiplier so the offline RBC PV-availability assumption
# remains explicit. Edit the CSV for a *new* study only after understanding it.
replay = ReplaySpec(
    sources=(ReplaySource(source_id="hourly_load", path=LOAD_PROFILE,
                          timestamp_column="time_utc", timezone_name="UTC"),),
    bindings=(ReplayBinding(source_id="hourly_load", kind="load",
                            targets=targets, mode="multiplier",
                            columns=("load_multiplier_pu",), units=("pu",)),),
    mode="strict", start_time_utc="2026-01-01T00:00:00Z",
    dt_seconds=3600, max_steps=STEPS,
)


# =============================================================================
# SECTION 4 - PROBLEMSPEC: select complete P1 observation/action authority
# =============================================================================
# This existing factory builds the SAME A04 ProblemSpec contract for RBC/MPC.
# The user studied explicit ObservationSpec and ActionSpec in Examples 04/05.
problem = make_p1_problem(
    pv=tuple(x.entity for x in case.pv),
    capacitors=tuple(x.entity for x in case.capacitors),
    transformers=tuple(x.entity for x in case.taps),
)


# =============================================================================
# SECTION 5 - CONSTRUCT AND RESET THE ENVIRONMENT
# =============================================================================
with TemporaryDirectory(prefix="opendsssim_e07_") as temporary:
    run = OUTPUT / RUN_NAME if SAVE_RESULTS else Path(temporary)
    if SAVE_RESULTS and run.exists():
        raise FileExistsError(f"Output already exists; choose a new RUN_NAME: {run}")
    run.mkdir(parents=True, exist_ok=True)
    env = OpenDSSSimulator(
        network=CIRCUIT, backend="altdss", problem=problem,
        exogenous_replay=replay, history_level="H1",
        inventory_dir=run / "Inventory",
        semantic_registry_dir=run / "SemanticRegistry",
        preflight_dir=run / "Preflight",
    )
    try:
        observation, info = env.reset(seed=RESET_SEED)
        if not info["solution"]["converged"]:
            raise RuntimeError("Reset AC power flow did not converge")
        print("\nEXAMPLE 07 - P1 RULE-BASED CONTROLLER")
        print("Network:", CIRCUIT)
        print("ProblemSpec:", problem.problem_spec_sha256)
        print("Gym action space:", env.action_space)
        print("PV/cap/reg counts:", len(case.pv), len(case.capacitors), len(case.taps))
        print("Reset voltages:", voltage_summary(observation))

        # =====================================================================
        # SECTION 6 - AUTHOR THE RBC MONITORS AND INSTANTIATE INSTALLED POLICY
        # =====================================================================
        first_state = env.controller_context(include_static_network=True)
        rbc = P1RuleBasedController(make_rbc_spec(first_state, case))
        pv_available_kw = {p.entity: float(p.available_kw[0]) for p in case.pv}
        if len(first_state.action_layout) != 21:
            raise RuntimeError("Expected 10 PV + 4 capacitor + 7 tap channels")

        # =====================================================================
        # SECTION 7 - SIMPLE CONTROLLER ADAPTER: STATE + FORECASTS -> ACTION
        # =====================================================================
        def controller(state, forecasts):
            # This RBC uses *current* bus voltages and present PV availability.
            # An exogenous load forecast may exist, but RBC does not need it.
            action, decision_details = rbc.decide(
                state, pv_available_kw=pv_available_kw)
            return action

        # =====================================================================
        # SECTION 8 - EXPLICIT CLOSED LOOP: caller retains env.step() authority
        # =====================================================================
        rows, audits = [], []
        for step in range(1, STEPS + 1):
            state = env.controller_context(forecast_horizon=1, required=False)
            forecasts = state.forecast
            action = controller(state, forecasts)
            if not env.action_space.contains(action):
                raise RuntimeError("RBC returned a Gym action outside ProblemSpec")
            observation, reward, terminated, truncated, info = env.step(action)
            if not info["solution"]["converged"]:
                raise RuntimeError(f"AC solve failed at step {step}")
            rbc.on_success(state, action, info)  # memory only AFTER success
            v = voltage_summary(observation)
            audit = list(info["action_audit"])
            if PRINT_ACTIONS:
                print("Nested Gym action:", action)
            if PRINT_VOLTAGES:
                print(f"Step {step:02d} | V=[{v['vmin_pu']:.4f},"
                      f" {v['vmax_pu']:.4f}] pu | out-of-band={v['outside_095_105']}"
                      f" | applied={sum(a['status']=='ADMISSIBLE_APPLIED' for a in audit)}")
            rows.append({"step": step,
                         "time_utc": info["time"]["electrical_sample_time_utc"],
                         "ac_converged": True, **v,
                         "requested_action_channels": len(audit),
                         "source_power_kw": info["solution"].get("total_power_kw"),
                         "reward": reward})
            audits.append({"step": step, "audits": audit})
            if terminated or truncated:
                if step != STEPS:
                    raise RuntimeError("Episode terminated before requested steps")
                break

        # =====================================================================
        # SECTION 9 - OPTIONAL EXPORTS AND RESOURCE CLEANUP
        # =====================================================================
        if SAVE_RESULTS:
            with (run / "voltage_and_control_steps.csv").open(
                    "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0]))
                writer.writeheader(); writer.writerows(rows)
            def save(filename, value):
                (run / filename).write_text(json.dumps(
                    value, indent=2, default=lambda v: v.tolist()
                    if hasattr(v, "tolist") else str(v)) + "\n", encoding="utf-8")
            save("problem_spec.json", problem.semantic_dict())
            save("action_audit_per_step.json", audits)
            save("initial_controller_context.json", first_state.to_dict())
            save("history.json", env.history.records)
            save("run_metadata.json", {"example": 7, "steps": len(rows),
                 "controller": "INSTALLED_P1_RBC", "constant_PV_availability": True,
                 "feeder_sha256": file_sha256(CIRCUIT),
                 "case_sha256": file_sha256(CASE_FILE),
                 "native_experiment": True})
            print("Saved:", run)
        else:
            print("SAVE_RESULTS=False: no permanent results")
    finally:
        env.close()
