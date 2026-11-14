"""EXAMPLE 09 - P2 GRAPH RESTORATION RBC (IEEE-123 MF01 / MF02).

PREAMBLE
========
Aim
    Learn how OpenDSSSim represents switch authority and fixed faults, then
    execute a 24-hour continuation of an *already electrically screened* RBC
    restoration route with an explicit user-owned environment.step() loop.

    P2GraphController.preview() is ONLY a radial graph/service calculation.
    Its decide() requires a separately qualified electrical evaluator. This
    tutorial does NOT fabricate that evaluator: every selected physical route
    is checked against a pinned S10D native AC screening before replay, and
    every subsequent environment step is checked using new AC observations.

Sections: 1 imports; 2 settings; 3 data; 4 ProblemSpec; 5 reset;
          6 controller setup; 7 controller(state,forecasts); 8 loop;
          9 optional outputs/close.

Inputs: Input/IEEE123_P2_MF01, Input/IEEE123_P2_MF02,
        Input/ControllerCases/*_lindist_case.json,
        Input/ControllerCases/RBC_S10D_P2_Results_QUALIFIED.zip.
Outputs: Output/<RUN_NAME> when SAVE_RESULTS=True.

Caveats: constant hourly replay; nominal connected-kW is a topology proxy;
         voltage-only qualification is NOT thermal/security certification;
         this is not 24 independent RBC electrical optimizations.
"""

# =============================================================================
# SECTION 1 - IMPORTS: existing reference controller and public action encoder
# =============================================================================
import csv
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import numpy as np

from opendsssim.environment import OpenDSSSimulator, ReplaySource, ReplayBinding, ReplaySpec
from opendsssim.controllers.reference import (
    make_p2_problem, P2GraphController, P2Load, encode_action,
)
from opendsssim.controllers.reference.contracts import observed
from opendsssim.controllers.mpc.closed_loop_a07a2 import p2_case_from_json


# =============================================================================
# SECTION 2 - USER SETTINGS
# =============================================================================
HERE = Path(__file__).resolve().parent
INPUT = HERE / "Input"
CASE_DIR = INPUT / "ControllerCases"
SCENARIO = "MF01"            # Choose "MF01" or "MF02"
STEPS = 3                    # 1..24 after future native smoke qualification
SAVE_RESULTS = True
PRINT_SWITCH_ACTIONS = False
RUN_NAME = "09_p2_rbc_mf01"   # Use a NEW name if you change scenario/run length
RESET_SEED = 511

SCENARIOS = {
    "MF01": ("IEEE123_P2_MF01", "ieee123_p2_mf01_simple", "MF01_RATIFIED_PARTIAL"),
    "MF02": ("IEEE123_P2_MF02", "ieee123_p2_mf02_exotic", "MF02_ROUTE_A"),
}
EXPECTED_S10D_SHA256 = "E2B37D6D7EB18E378497B32606F34433BF23B99F7D20AF8FBE4929BF5A14C4F0"


def voltage_summary(obs):
    values = [float(v) for data in obs.get("current", {}).get("Bus", {}).values()
              for v in np.asarray(data.get("bus_voltage_pu", []), dtype=float).reshape(-1)
              if np.isfinite(v) and v > 1e-4]
    return {"vmin_pu": min(values) if values else None,
            "vmax_pu": max(values) if values else None,
            "outside_095_105": sum(v < 0.95 or v > 1.05 for v in values)}


def audit_switch_readback(audit, faulted):
    """Healthy switch requests must match terminal-open feedback exactly."""
    faulted = {x.casefold() for x in faulted}
    matched, disabled = 0, 0
    for record in audit:
        entity, status = record["native_entity"].casefold(), record["status"]
        if status == "FAULT_DISABLED" and entity in faulted:
            if bool(record.get("requested_value")):
                raise RuntimeError("Fault-disabled switch was requested closed")
            disabled += 1
            continue
        if status != "ADMISSIBLE_APPLIED":
            raise RuntimeError("Unapplied P2 action: " + entity)
        if entity.startswith("line."):
            flags = record.get("realized_value")
            if not isinstance(flags, (list, tuple)) or not flags:
                raise RuntimeError("Missing physical switch readback: " + entity)
            realized_closed = not any(bool(value) for value in flags)
            if realized_closed != bool(record["requested_value"]):
                raise RuntimeError("Requested/realized switch state mismatch: " + entity)
            matched += 1
    return matched, disabled


# =============================================================================
# SECTION 3 - LOAD THE STATIC P2 CASE AND VERIFIED HISTORICAL ROUTE
# =============================================================================
if SCENARIO not in SCENARIOS or not 1 <= STEPS <= 24:
    raise ValueError("Choose MF01/MF02 and steps in 1..24")
feed_folder, feeder_id, selected_route = SCENARIOS[SCENARIO]
CIRCUIT = INPUT / feed_folder / "IEEE123Master.dss"
CASE_FILE = CASE_DIR / (feeder_id + "_lindist_case.json")
S10D_FILE = CASE_DIR / "RBC_S10D_P2_Results_QUALIFIED.zip"
PROFILE = CASE_DIR / "constant_hourly_load_multiplier.csv"
TARGETS_FILE = INPUT / "ieee123_load_targets.csv"
for required in (CIRCUIT, CASE_FILE, S10D_FILE, PROFILE, TARGETS_FILE):
    if not required.is_file():
        raise FileNotFoundError(required)
case = p2_case_from_json(json.loads(CASE_FILE.read_text(encoding="utf-8")))
if hashlib.sha256(S10D_FILE.read_bytes()).hexdigest().upper() != EXPECTED_S10D_SHA256:
    raise RuntimeError("S10D route evidence has changed")
with ZipFile(S10D_FILE) as archive:
    if archive.testzip() is not None:
        raise RuntimeError("S10D route ZIP damaged")
    saved_preview = json.loads(archive.read(feeder_id + "/structural_preview.json"))
    saved_audit = json.loads(archive.read(feeder_id + "/live_action_audit_step1.json"))
if saved_preview.get("status") != "STRUCTURAL_ONLY_NOT_ELECTRICALLY_QUALIFIED":
    raise RuntimeError("Historical RBC preview provenance mismatch")
selected_states = {}
for record in saved_audit:
    entity = record["native_entity"].casefold()
    closed = bool(int(record["requested_value"]))
    if bool(saved_preview["states"][entity]) != closed:
        raise RuntimeError("Saved S10D preview/action inconsistency")
    if record["status"] not in ("FAULT_DISABLED", "ADMISSIBLE_APPLIED"):
        raise RuntimeError("Saved S10D action not admissible")
    selected_states[entity] = closed

faulted = tuple(b.name for b in case.branches if not b.healthy)
with TARGETS_FILE.open(newline="", encoding="utf-8") as f:
    loads_for_replay = tuple(row["native_load"] for row in csv.DictReader(f))
if len(loads_for_replay) != 91:
    raise RuntimeError("Expected 91 declared IEEE-123 loads")
replay = ReplaySpec(
    sources=(ReplaySource(source_id="loads", path=PROFILE,
                          timestamp_column="time_utc", timezone_name="UTC"),),
    bindings=(ReplayBinding(source_id="loads", kind="load", targets=loads_for_replay,
                            mode="multiplier", columns=("load_multiplier_pu",),
                            units=("pu",)),),
    mode="strict", start_time_utc="2026-01-01T00:00:00Z",
    dt_seconds=3600, max_steps=STEPS,
)


# =============================================================================
# SECTION 4 - PROBLEMSPEC: all switches; fault health is an A04 FaultSpec
# =============================================================================
problem = make_p2_problem(
    switches=tuple(case.initial_switches),
    curtailable_loads=tuple(l.entity for l in case.loads if l.curtailable),
    faulted=faulted,
)


# =============================================================================
# SECTION 5 - CREATE AND RESET A REAL OPENDSSSIM ENVIRONMENT
# =============================================================================
with TemporaryDirectory(prefix="opendsssim_e09_") as temporary:
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
            raise RuntimeError("P2 reset AC failed")
        print("\nEXAMPLE 09 - P2 RBC", SCENARIO, "selected route", selected_route)
        print("Faults:", faulted, "| action space:", env.action_space)
        print("Initial AC voltage:", voltage_summary(obs))

        # =====================================================================
        # SECTION 6 - EXISTING GRAPH CONTROLLER (NO NEW ELECTRICAL EVALUATOR)
        # =====================================================================
        loads = tuple(P2Load(x.entity, x.bus, x.priority, x.curtailable)
                      for x in case.loads)
        graph_controller = P2GraphController(loads=loads, faulted=faulted)
        route_info = {}

        # =====================================================================
        # SECTION 7 - STATE + FORECASTS -> COMPLETE GYM ACTION
        # =====================================================================
        def controller(state, forecasts):
            # preview() returns a structural proposal only; this function will
            # NEVER apply it unless it matches the *previously electrically
            # screened* S10D switch vector exactly (including faulted SW7).
            preview = graph_controller.preview(state)
            current = {k.casefold(): bool(v) for k, v in preview.states.items()}
            if current != selected_states or preview.action is not None:
                raise RuntimeError("Current RBC structural route != S10D qualified route")
            commands = {}
            for entry in state.action_layout:
                cls, obj, quantity = entry["path"]
                key = (cls + "." + obj).casefold()
                if quantity != "branch_switch_command" or key not in selected_states:
                    raise RuntimeError("Unexpected P2 action in ProblemSpec")
                commands[(cls + "." + obj, quantity)] = (
                    "CLOSED" if selected_states[key] else "OPEN")
            connected = [ld for ld in loads
                         if preview.service[ld.native_entity] > 0.5]
            nominal_kw = sum(float(observed(state, ld.native_entity,
                                            "load_available_active_demand_kw"))
                             for ld in connected)
            route_info.clear()
            route_info.update({"nominal_connected_kw_proxy": nominal_kw,
                               "connected_load_count": len(connected),
                               "radial_candidates": preview.diagnostics["radial_candidates"]})
            return encode_action(state, commands)

        # =====================================================================
        # SECTION 8 - USER-OWNED LOOP: NEW AC VALIDATION AT EVERY HOUR
        # =====================================================================
        rows, audits = [], []
        for step in range(1, STEPS + 1):
            state = env.controller_context(forecast_horizon=2, required=False,
                                            include_static_network=True)
            forecasts = state.forecast
            action = controller(state, forecasts)
            if not env.action_space.contains(action):
                raise RuntimeError("RBC action is not authorized by ProblemSpec")
            obs, reward, terminated, truncated, info = env.step(action)
            if not info["solution"]["converged"]:
                raise RuntimeError("P2 AC did not converge")
            audits_now = list(info["action_audit"])
            matched, disabled = audit_switch_readback(audits_now, faulted)
            v = voltage_summary(obs)
            if v["outside_095_105"]:
                raise RuntimeError("RBC route failed exploratory voltage band")
            print(f"Step {step:02d}: {route_info['nominal_connected_kw_proxy']:.1f} "
                  f"nominal kW | AC V={v['vmin_pu']:.4f}..{v['vmax_pu']:.4f} "
                  f"| healthy switch readbacks={matched}")
            if PRINT_SWITCH_ACTIONS:
                print("Gym action:", action, "\nReadbacks:", audits_now)
            rows.append({"step": step,
                         "time_utc": info["time"]["electrical_sample_time_utc"],
                         "route": selected_route, **route_info, **v,
                         "ac_converged": True,
                         "healthy_switch_matches": matched,
                         "fault_disabled_action_entries": disabled,
                         "reward": reward})
            audits.append({"step": step, "audit": audits_now})
            if terminated or truncated:
                if step != STEPS:
                    raise RuntimeError("Early termination")
                break

        # =====================================================================
        # SECTION 9 - OPTIONAL SAVES AND CLOSE
        # =====================================================================
        if SAVE_RESULTS:
            with (run / "rbc_restoration_steps.csv").open(
                    "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
            def save(name, obj):
                (run / name).write_text(json.dumps(obj, indent=2,
                    default=lambda v: v.tolist() if hasattr(v, "tolist") else str(v)
                    ) + "\n", encoding="utf-8")
            save("problem_spec.json", problem.semantic_dict())
            save("switch_readbacks.json", audits)
            save("history.json", env.history.records)
            save("provenance.json", {"scenario": feeder_id, "route": selected_route,
                 "RBC_route_origin": "S10D_PINNED_AC_SCREEN",
                 "independent_fresh_electrical_decisions": False,
                 "native_AC_validation_per_step": True,
                 "nominal_connected_kw_not_measured_AC_energy": True,
                 "thermal_certification": False})
            print("Saved:", run)
        else:
            print("SAVE_RESULTS=False: no permanent results")
    finally:
        env.close()
