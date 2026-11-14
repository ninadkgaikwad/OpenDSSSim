"""EXAMPLE 08 - P1 RECEDING-HORIZON MPC (IEEE-123 Volt/VAR).

PREAMBLE
========
Aim
    Reuse the *installed* P1 LinDistFlow mixed-integer quadratic optimizer.
    At each hour: inspect ControllerContext, update the qualified horizon-12
    static model, solve Gurobi, encode the FIRST decision, and execute one
    official OpenDSSSimulator.step(action). The AC result is authoritative.

Sections: 1 imports; 2 settings; 3 model/replay; 4 ProblemSpec; 5 reset;
          6 controller(state,forecasts); 7 user-owned loop; 8 optional saves.

Inputs
    Input/IEEE123_P1/IEEE123Master.dss
    Input/ControllerCases/ieee123_pesgm2027_lindist_case.json
    Input/ControllerCases/ieee123_pesgm2027_static_discovery.json
    Input/ControllerCases/constant_hourly_load_multiplier.csv

Assumptions
    P1 horizon=12; native 10 PV, 4 capacitors, 7 regulators. A static
    *offline-qualified approximation* is updated from public observations
    and declared exogenous forecasts. This is not a real-time AC optimizer.
    Physical replay is hourly. Requires working Gurobi; model execution
    is deliberately not performed by the lesson installer.
"""

# =============================================================================
# SECTION 1 - IMPORTS: installed control code, no cloned MPC implementation
# =============================================================================
import csv
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import numpy as np

from opendsssim.environment import OpenDSSSimulator, ReplaySource, ReplayBinding, ReplaySpec
from opendsssim.controllers.reference import make_p1_problem
from opendsssim.controllers.mpc.closed_loop_a07a2 import (
    p1_case_from_json, update_p1, p1_action,
)
from opendsssim.controllers.mpc.p1_miqp import solve_p1


# =============================================================================
# SECTION 2 - USER SETTINGS
# =============================================================================
HERE = Path(__file__).resolve().parent
INPUT = HERE / "Input"
CASE_DIR = INPUT / "ControllerCases"
CIRCUIT = INPUT / "IEEE123_P1" / "IEEE123Master.dss"
CASE_FILE = CASE_DIR / "ieee123_pesgm2027_lindist_case.json"
DISCOVERY = CASE_DIR / "ieee123_pesgm2027_static_discovery.json"
PROFILE = CASE_DIR / "constant_hourly_load_multiplier.csv"
TARGETS_FILE = INPUT / "ieee123_load_targets.csv"
OUTPUT = HERE / "Output"
RUN_NAME = "08_p1_mpc"
STEPS = 3
SAVE_RESULTS = True
PRINT_FULL_ACTIONS = False
SOLVER_TIME_LIMIT_SECONDS = 45.0
REQUIRE_OPTIMAL = True
RESET_SEED = 511


def voltage_summary(obs):
    vals = [float(v) for bus in obs.get("current", {}).get("Bus", {}).values()
            for v in np.asarray(bus.get("bus_voltage_pu", []), dtype=float).reshape(-1)
            if np.isfinite(v) and v > 1e-4]
    return {"vmin_pu": min(vals) if vals else None,
            "vmax_pu": max(vals) if vals else None,
            "outside_095_105": sum(v < 0.95 or v > 1.05 for v in vals),
            "energized_components": len(vals)}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


# =============================================================================
# SECTION 3 - LOAD PINNED CASE, PV REFERENCE, AND EXOGENOUS REPLAY INPUT
# =============================================================================
for path in (CIRCUIT, CASE_FILE, DISCOVERY, PROFILE, TARGETS_FILE):
    if not path.is_file():
        raise FileNotFoundError(path)
if not 1 <= STEPS <= 24 or not 1 <= SOLVER_TIME_LIMIT_SECONDS <= 600:
    raise ValueError("Invalid steps or solver time limit")
case = p1_case_from_json(json.loads(CASE_FILE.read_text(encoding="utf-8")))
if case.horizon != 12:
    raise ValueError("Expected qualified P1 horizon=12")

# This offline discovery record provides PV irradiance references. The actual
# decision-time state and forecast still come ONLY from ControllerContext.
discovery = json.loads(DISCOVERY.read_text(encoding="utf-8"))
reference_irradiance = {}
for item in discovery["native_discovery"]["objects"]:
    if item["full_name"].casefold().startswith("pvsystem."):
        reference_irradiance[item["full_name"].casefold()] = float(
            json.loads(item["properties_json"])["Irradiance"])
if set(reference_irradiance) != {x.entity.casefold() for x in case.pv}:
    raise RuntimeError("Qualified 10-PV irradiance reference is incomplete")
with TARGETS_FILE.open(newline="", encoding="utf-8") as f:
    targets = tuple(row["native_load"] for row in csv.DictReader(f))
if len(targets) != 91 or len({v.casefold() for v in targets}) != 91:
    raise RuntimeError("Expected 91 unique IEEE-123 loads")

replay = ReplaySpec(
    sources=(ReplaySource(source_id="loads", path=PROFILE,
                          timestamp_column="time_utc", timezone_name="UTC"),),
    bindings=(ReplayBinding(source_id="loads", kind="load", targets=targets,
                            mode="multiplier", columns=("load_multiplier_pu",),
                            units=("pu",)),),
    mode="strict", start_time_utc="2026-01-01T00:00:00Z",
    dt_seconds=3600, max_steps=STEPS,
)


# =============================================================================
# SECTION 4 - PROBLEMSPEC: same authorized P1 actions as the RBC example
# =============================================================================
problem = make_p1_problem(
    pv=tuple(p.entity for p in case.pv),
    capacitors=tuple(c.entity for c in case.capacitors),
    transformers=tuple(t.entity for t in case.taps),
)


# =============================================================================
# SECTION 5 - CONSTRUCT ENVIRONMENT, RESET, INSPECT STATE SPACE
# =============================================================================
with TemporaryDirectory(prefix="opendsssim_e08_") as temporary:
    run = OUTPUT / RUN_NAME if SAVE_RESULTS else Path(temporary)
    if SAVE_RESULTS and run.exists():
        raise FileExistsError(f"Choose another RUN_NAME: {run}")
    run.mkdir(parents=True, exist_ok=True)
    env = OpenDSSSimulator(
        network=CIRCUIT, backend="altdss", problem=problem,
        exogenous_replay=replay, history_level="H1",
        inventory_dir=run / "Inventory", semantic_registry_dir=run / "SemanticRegistry",
        preflight_dir=run / "Preflight",
    )
    try:
        obs, info = env.reset(seed=RESET_SEED)
        if not info["solution"]["converged"]:
            raise RuntimeError("Reset AC did not converge")
        print("\nEXAMPLE 08 - P1 MPC (Gurobi MIQP)")
        print("Horizon:", case.horizon, "| action space:", env.action_space)
        print("Initial voltage envelope:", voltage_summary(obs))
        latest = {}  # Just records the last solver report; NOT an env wrapper.

        # =====================================================================
        # SECTION 6 - THIN CONTROLLER ADAPTER: STATE + FORECASTS -> ACTION
        # =====================================================================
        def controller(state, forecasts):
            # update_p1 validates all action channels, native capacitor/tap
            # readbacks and the qualified forecast identity before creating
            # the latest controller-side linearized case.
            updated_case, forecast_details = update_p1(
                case, state, pv_reference_irradiance=reference_irradiance)
            result = solve_p1(updated_case, time_limit_s=SOLVER_TIME_LIMIT_SECONDS,
                              threads=1, output_flag=False)
            if REQUIRE_OPTIMAL and result.status != "OPTIMAL":
                raise RuntimeError("P1 MPC has no proven optimal incumbent")
            action = p1_action(state, result)  # first horizon decision only
            latest.clear()
            latest.update({"solver_status": result.status,
                           "objective": result.objective,
                           "forecast_provenance": forecast_details,
                           "solver_diagnostics": result.diagnostics})
            return action

        # =====================================================================
        # SECTION 7 - EXPLICIT CLOSED LOOP: one optimizer call, one AC step
        # =====================================================================
        rows, step_audits = [], []
        for step in range(1, STEPS + 1):
            state = env.controller_context(forecast_horizon=case.horizon,
                                            required=False, include_static_network=False)
            forecasts = state.forecast
            action = controller(state, forecasts)
            if not env.action_space.contains(action):
                raise RuntimeError("MPC action outside ProblemSpec Gym space")
            obs, reward, terminated, truncated, info = env.step(action)
            if not info["solution"]["converged"]:
                raise RuntimeError(f"P1 AC failed on step {step}")
            audit = list(info["action_audit"])
            if any(a["status"] != "ADMISSIBLE_APPLIED" for a in audit):
                raise RuntimeError("P1 control command was not accepted")
            # A native capacitor *readback* may differ from the requested
            # state despite ADMISSIBLE_APPLIED. Preserve both, do not fabricate
            # equality or bypass the public actuator pathway.
            v = voltage_summary(obs)
            print(f"Step {step:02d}: {latest['solver_status']} | "
                  f"AC V={v['vmin_pu']:.4f}..{v['vmax_pu']:.4f} pu | "
                  f"violating components={v['outside_095_105']}")
            if PRINT_FULL_ACTIONS:
                print("Action:", action, "\nAudit:", audit)
            rows.append({"step": step, "time_utc": info["time"]["electrical_sample_time_utc"],
                         "solver_status": latest["solver_status"],
                         "solver_objective": latest["objective"],
                         "ac_converged": True, **v,
                         "applied_channels": len(audit), "reward": reward})
            step_audits.append({"step": step, "solver": dict(latest), "audit": audit})
            if terminated or truncated:
                if step != STEPS:
                    raise RuntimeError("Early termination")
                break

        # =====================================================================
        # SECTION 8 - OPTIONAL OUTPUTS / CLOSE
        # =====================================================================
        if SAVE_RESULTS:
            with (run / "mpc_voltage_steps.csv").open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
            def save(name, value):
                (run / name).write_text(json.dumps(
                    value, indent=2, default=lambda v: v.tolist()
                    if hasattr(v, "tolist") else str(v)) + "\n", encoding="utf-8")
            save("problem_spec.json", problem.semantic_dict())
            save("solver_and_action_audit.json", step_audits)
            save("history.json", env.history.records)
            save("provenance.json", {"case_sha256": sha(CASE_FILE),
                 "native_feeder_sha256": sha(CIRCUIT),
                 "solver": "INSTALLED_P1_MIQP", "model_horizon": case.horizon,
                 "physical_replay_dt_hours": 1.0,
                 "linear_model_is_AC_truth": False})
            print("Saved:", run)
        else:
            print("SAVE_RESULTS=False: no permanent results")
    finally:
        env.close()
