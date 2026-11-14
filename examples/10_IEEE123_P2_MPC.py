"""EXAMPLE 10 - P2 RESTORATION MPC (IEEE-123 MF01 OR MF02).

PREAMBLE
========
Aim
    Run the installed P2 horizon-2 LinDistFlow restoration MILP with
    decision-time ControllerContext and an explicit env.step(action) loop.
    The selected *first* switch action is applied to a true native AC circuit.

Scientific objective selection
    POLICY = 'slack-first': original frozen P2 solver. Its lexicographic
        hierarchy prioritizes operational voltage-model slack over service.
    POLICY = 'service-first': separately qualified *sensitivity*, stored as
        an explicitly pinned, external example-side solver source. ONLY the
        two Gurobi objective priorities change. No installed P2 source or
        frozen simulator file is changed, and the alternative is NOT silently
        presented as the original formulation.

Sections: 1 imports; 2 settings; 3 cases/replay; 4 ProblemSpec;
          5 reset; 6 controller(state, forecasts); 7 loop; 8 saves.

Inputs: Input/IEEE123_P2_MF01 or IEEE123_P2_MF02,
        Input/ControllerCases/*_lindist_case.json, P2 sensitivity solver.
Outputs: Output/<RUN_NAME> only when SAVE_RESULTS=True.

Important: model dt_hours=0.25 is an optimization objective unit. Physical
replay steps are one hour. Connected-load kW is NOT delivered AC-metered kW.
Bus-level radiality and voltage-only AC checking do not certify thermal or
phase-specific security. The forecast never exposes future AC state.
"""

# =============================================================================
# SECTION 1 - IMPORTS (INSTALLED MPC AND GYMNASIUM ENVIRONMENT)
# =============================================================================
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import numpy as np

from opendsssim.environment import OpenDSSSimulator, ReplaySource, ReplayBinding, ReplaySpec
from opendsssim.controllers.reference import make_p2_problem
from opendsssim.controllers.mpc.closed_loop_a07a2 import (
    p2_case_from_json, update_p2, p2_action,
)
from opendsssim.controllers.mpc import p2_milp


# =============================================================================
# SECTION 2 - USER SETTINGS
# =============================================================================
HERE = Path(__file__).resolve().parent
INPUT = HERE / "Input"
CASE_DIR = INPUT / "ControllerCases"
SCENARIO = "MF01"              # MF01 or MF02
POLICY = "service-first"       # 'slack-first' or 'service-first'
STEPS = 3                      # Set 24 for complete 24-hour case
SAVE_RESULTS = True
PRINT_SWITCH_ACTIONS = False
REQUIRE_OPTIMAL = True
SOLVER_TIME_LIMIT_SECONDS = 45.0
RUN_NAME = "10_p2_mpc_mf01_service_first"
RESET_SEED = 511

SCENARIOS = {
    "MF01": ("IEEE123_P2_MF01", "ieee123_p2_mf01_simple"),
    "MF02": ("IEEE123_P2_MF02", "ieee123_p2_mf02_exotic"),
}
ORIGINAL_SOLVER_SHA256 = "E1196DA89E23DE77127DA71BD993D2F595B2E62C73D82D1FB64C6FBF0131300E"
SERVICE_FIRST_FILE = CASE_DIR / "p2_service_first_sensitivity_solver.py"


def voltage_summary(obs):
    values = [float(v) for bus in obs.get("current", {}).get("Bus", {}).values()
              for v in np.asarray(bus.get("bus_voltage_pu", []), dtype=float).reshape(-1)
              if np.isfinite(v) and v > 1e-4]
    return {"vmin_pu": min(values) if values else None,
            "vmax_pu": max(values) if values else None,
            "outside_095_105": sum(v < 0.95 or v > 1.05 for v in values)}


def check_switch_readbacks(audits, faulted):
    """Check switch realized terminal-open vectors; don't count faulted SW7."""
    fault = {name.casefold() for name in faulted}
    matched = 0
    for record in audits:
        name, status = record["native_entity"].casefold(), record["status"]
        if status == "FAULT_DISABLED" and name in fault:
            if bool(record.get("requested_value")):
                raise RuntimeError("Fault-disabled switch requested CLOSED")
            continue
        if status != "ADMISSIBLE_APPLIED":
            raise RuntimeError("Unapplied MPC action: " + name)
        if name.startswith("line."):
            flags = record.get("realized_value")
            if not isinstance(flags, (list, tuple)) or not flags:
                raise RuntimeError("Missing switch terminal readback: " + name)
            if (not any(bool(x) for x in flags)) != bool(record["requested_value"]):
                raise RuntimeError("MPC switch requested/realized mismatch: " + name)
            matched += 1
    return matched


def select_qualified_p2_solver(policy):
    """Use installed MILP, or pin the *external* service-first science variant.

    We do not monkeypatch opendsssim or edit frozen source. The optional file is
    checked byte-for-byte against EXACTLY two changes in the original solver.
    """
    original = Path(p2_milp.__file__).read_bytes()
    if hashlib.sha256(original).hexdigest().upper() != ORIGINAL_SOLVER_SHA256:
        raise RuntimeError("Installed P2 MILP does not match qualified R02 source")
    if policy == "slack-first":
        return p2_milp.solve_p2
    if policy != "service-first":
        raise ValueError("POLICY must be 'slack-first' or 'service-first'")
    source = original.decode("utf-8")
    old_slack = "m.setObjectiveN(op,0,priority=3,"
    old_unserved = "m.setObjectiveN(unserved,1,priority=2,"
    if source.count(old_slack) != 1 or source.count(old_unserved) != 1:
        raise RuntimeError("Objective source positions are not uniquely identified")
    expected = source.replace(old_slack, "m.setObjectiveN(op,0,priority=2,")
    expected = expected.replace(old_unserved, "m.setObjectiveN(unserved,1,priority=3,")
    if SERVICE_FIRST_FILE.read_bytes() != expected.encode("utf-8"):
        raise RuntimeError("Service-first file has changes beyond two priorities")
    # Load under the parent package so relative imports refer to the same
    # already-qualified contracts/dataclasses; never change p2_milp.solve_p2.
    name = "opendsssim.controllers.mpc._p2_service_first_course"
    spec = importlib.util.spec_from_file_location(name, SERVICE_FIRST_FILE)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load external P2 sensitivity module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    # Prevent a .pyc cache from being written into immutable Input/ data.
    previous_bytecode_setting = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    finally:
        sys.dont_write_bytecode = previous_bytecode_setting
    return module.solve_p2


# =============================================================================
# SECTION 3 - READ STATIC CASE AND DECLARE PHYSICAL LOAD REPLAY
# =============================================================================
if SCENARIO not in SCENARIOS or POLICY not in ("slack-first", "service-first"):
    raise ValueError("Unknown P2 case or objective policy")
if not 1 <= STEPS <= 24 or not 1 <= SOLVER_TIME_LIMIT_SECONDS <= 600:
    raise ValueError("Invalid STEPS or solver time limit")
folder, feeder_id = SCENARIOS[SCENARIO]
CIRCUIT = INPUT / folder / "IEEE123Master.dss"
CASE_FILE = CASE_DIR / (feeder_id + "_lindist_case.json")
PROFILE = CASE_DIR / "constant_hourly_load_multiplier.csv"
TARGETS_FILE = INPUT / "ieee123_load_targets.csv"
for path in (CIRCUIT, CASE_FILE, PROFILE, TARGETS_FILE):
    if not path.is_file():
        raise FileNotFoundError(path)
case = p2_case_from_json(json.loads(CASE_FILE.read_text(encoding="utf-8")))
if case.horizon != 2:
    raise RuntimeError("Expected qualified P2 horizon=2")
faulted = tuple(branch.name for branch in case.branches if not branch.healthy)
with TARGETS_FILE.open(newline="", encoding="utf-8") as f:
    targets = tuple(row["native_load"] for row in csv.DictReader(f))
if len(targets) != 91:
    raise RuntimeError("Expected 91 load targets")
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
# SECTION 4 - PROBLEMSPEC: EXTERNAL SWITCH CONTROL + DECLARED STATIC FAULTS
# =============================================================================
problem = make_p2_problem(
    switches=tuple(case.initial_switches),
    curtailable_loads=tuple(x.entity for x in case.loads if x.curtailable),
    faulted=faulted,
)


# =============================================================================
# SECTION 5 - CONSTRUCT/RESET ENV; SELECT SOLVER ONLY ONCE
# =============================================================================
with TemporaryDirectory(prefix="opendsssim_e10_") as temporary:
    run = HERE / "Output" / RUN_NAME if SAVE_RESULTS else Path(temporary)
    if SAVE_RESULTS and run.exists():
        raise FileExistsError(f"Choose unused RUN_NAME: {run}")
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
            raise RuntimeError("Reset P2 AC did not converge")
        solve = select_qualified_p2_solver(POLICY)
        print("\nEXAMPLE 10 - P2 MPC", SCENARIO, POLICY)
        print("Case horizon:", case.horizon, "| declared faults:", faulted)
        print("ProblemSpec action space:", env.action_space)
        print("Reset AC envelope:", voltage_summary(obs))
        latest = {}

        # =====================================================================
        # SECTION 6 - THIN CONTROLLER: PUBLIC STATE/FORECAST -> MILP -> ACTION
        # =====================================================================
        def controller(state, forecasts):
            updated, forecast_details = update_p2(case, state)
            solved = solve(updated, time_limit_s=SOLVER_TIME_LIMIT_SECONDS,
                           threads=1, output_flag=False)
            if REQUIRE_OPTIMAL and solved.status != "OPTIMAL":
                raise RuntimeError("P2 MPC did not prove optimality")
            action = p2_action(state, solved)  # FIRST switch vector only
            latest.clear()
            latest.update({"solver_status": solved.status,
                           "objectives": solved.objectives,
                           "forecast_provenance": forecast_details,
                           "solver_diagnostics": solved.diagnostics})
            return action

        # =====================================================================
        # SECTION 7 - EXPLICIT RECeding-HORIZON LOOP AND AC READBACK
        # =====================================================================
        rows, audits = [], []
        for step in range(1, STEPS + 1):
            state = env.controller_context(forecast_horizon=case.horizon,
                                            required=False, include_static_network=False)
            forecasts = state.forecast
            action = controller(state, forecasts)
            if not env.action_space.contains(action):
                raise RuntimeError("P2 MPC command outside Gym action space")
            obs, reward, terminated, truncated, info = env.step(action)
            if not info["solution"]["converged"]:
                raise RuntimeError("P2 native AC failed")
            action_audit = list(info["action_audit"])
            matches = check_switch_readbacks(action_audit, faulted)
            v = voltage_summary(obs)
            print(f"Step {step:02d}: {latest['solver_status']} | "
                  f"AC V={v['vmin_pu']:.4f}..{v['vmax_pu']:.4f} | "
                  f"out-of-band={v['outside_095_105']} | "
                  f"healthy switches matched={matches}")
            if PRINT_SWITCH_ACTIONS:
                print("Action:", action, "\nAudit:", action_audit)
            rows.append({"step": step,
                         "time_utc": info["time"]["electrical_sample_time_utc"],
                         "policy": POLICY,
                         "solver_status": latest["solver_status"],
                         "model_operational_slack": latest["objectives"].get("operational_slack"),
                         "model_weighted_unserved_kwh": latest["objectives"].get("weighted_unserved_kwh"),
                         "model_switching_effort": latest["objectives"].get("switching_effort"),
                         "healthy_switch_matches": matches,
                         "ac_converged": True, **v, "reward": reward})
            audits.append({"step": step, "solver": dict(latest),
                           "action_audit": action_audit})
            if terminated or truncated:
                if step != STEPS:
                    raise RuntimeError("Early termination")
                break

        # =====================================================================
        # SECTION 8 - OPTIONAL OUTPUT, MODEL PROVENANCE, CLOSE
        # =====================================================================
        if SAVE_RESULTS:
            with (run / "mpc_restoration_steps.csv").open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
            def save(name, value):
                (run / name).write_text(json.dumps(value, indent=2,
                    default=lambda v: v.tolist() if hasattr(v, "tolist") else str(v)
                    ) + "\n", encoding="utf-8")
            save("problem_spec.json", problem.semantic_dict())
            save("solver_and_action_audit.json", audits)
            save("history.json", env.history.records)
            save("provenance.json", {"scenario": feeder_id, "objective_policy": POLICY,
                 "installed_solver_sha256": ORIGINAL_SOLVER_SHA256,
                 "external_model_priority_sensitivity": POLICY == "service-first",
                 "static_case_sha256": hashlib.sha256(CASE_FILE.read_bytes()).hexdigest().upper(),
                 "physical_replay_dt_hours": 1.0, "optimizer_dt_hours": case.dt_hours,
                 "model_kwh_not_delivered_AC_energy": True,
                 "thermal_certification": False})
            print("Saved:", run)
        else:
            print("SAVE_RESULTS=False: no permanent results")
    finally:
        env.close()
