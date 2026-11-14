"""B00I1 four-variant native-as-installed time-series pilot.

Experiment runner, not a controller implementation. Uses A05I3 replay and the
public A04/A05 client surface; no direct backend/Plant access or extra solves.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from typing import Any

import numpy as np

from opendsssim.controllers.baselines import NativeControlsBaseline
from opendsssim.environment import OpenDSSSimulator, ReplayBinding, ReplaySource, ReplaySpec
from opendsssim.problem import (
    ActionSpec, ControlAuthorityMode, ControlAuthoritySpec, DeviceRef,
    FaultSpec, ObservationSpec, ProblemSpec, RegistryKind,
    SelectionGroup, SemanticQuery,
)
from opendsssim.runtime import HistoryLevel


PRIMARY = (
    "ieee123_base", "ieee123_pesgm2027",
    "ieee123_p2_mf01_simple", "ieee123_p2_mf02_exotic",
)
# Explicit ratified PRE *static* health, not a restoration decision.
PRE_FAULTS = {
    "ieee123_base": (),
    "ieee123_pesgm2027": (),
    "ieee123_p2_mf01_simple": ("Line.L45", "Line.L77", "Line.L93", "Line.Sw7"),
    "ieee123_p2_mf02_exotic": ("Line.L45", "Line.L77", "Line.L93"),
}
EXPERIMENT_SCHEMA = "B00I1.native_as_installed.v01"


class B00ExperimentError(RuntimeError):
    pass


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest().upper()


def _entities_from_dss(file: Path, cls: str) -> tuple[str, ...]:
    if not file.is_file():
        raise B00ExperimentError(f"MISSING_DEVICE_DEFINITION: {file}")
    pattern = re.compile(r"^\s*new\s+" + re.escape(cls) + r"\.([^\s!]+)", re.I)
    names: list[str] = []
    for raw in file.read_text(encoding="utf-8-sig").splitlines():
        match = pattern.search(raw)
        if match:
            names.append(f"{cls}.{match.group(1)}")
    if not names or len(names) != len({x.casefold() for x in names}):
        raise B00ExperimentError(f"INVALID_{cls.upper()}_DEFINITIONS: {file}")
    return tuple(names)


def make_problem(feeder: str) -> ProblemSpec:
    if feeder not in PRIMARY:
        raise B00ExperimentError(f"UNRATIFIED_B00_FEEDER: {feeder}")
    faults = PRE_FAULTS[feeder]
    return ProblemSpec.create(
        "pesgm2027-b00-native-as-installed", "1",
        observations=ObservationSpec(groups=(SelectionGroup("native_timeseries", (
            SemanticQuery(RegistryKind.STATE, quantity="solution_converged"),
            SemanticQuery(RegistryKind.STATE, quantity="bus_voltage_pu"),
        )),)),
        actions=ActionSpec(),
        control_authority=ControlAuthoritySpec(mode=ControlAuthorityMode.NATIVE),
        faults=() if not faults else (FaultSpec(
            "P2_FROZEN_PRE_HEALTH", tuple(DeviceRef(item) for item in faults)),),
        metadata={"baseline": "NATIVE_AS_INSTALLED", "feeder": feeder,
                  "static_health": "PRE" if faults else "NONE", "switch_policy": "NO_EXTERNAL_ACTIONS"},
    )


def _csv(path: Path, samples: list[tuple[str, float]], label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("timestamp_utc", label))
        writer.writerows(samples)


def make_replay(
    *, feeder_dir: Path, output_dir: Path, steps: int, start: str,
    dt_seconds: int, load_curve: tuple[float, ...], pv_curve: tuple[float, ...],
) -> tuple[ReplaySpec, dict[str, Any]]:
    if steps < 2 or len(load_curve) != steps or len(pv_curve) != steps:
        raise B00ExperimentError("B00_REPLAY_LENGTH_MISMATCH")
    load_targets = _entities_from_dss(feeder_dir / "IEEE123Loads.DSS", "Load")
    # The four primary variants all inherit 91 load objects. Fail closed on drift.
    if len(load_targets) != 91:
        raise B00ExperimentError(f"IEEE123_LOAD_COUNT_DRIFT: {len(load_targets)}")
    master_text = (feeder_dir / "IEEE123Master.dss").read_text(encoding="utf-8-sig")
    if not re.search(r"(?im)^\s*redirect\s+IEEE123Loads\.DSS\s*(?:!.*)?$", master_text):
        raise B00ExperimentError("MASTER_LOAD_REDIRECT_MISSING")
    times = [
        (datetime.fromisoformat(start.replace("Z", "+00:00")) + timedelta(seconds=dt_seconds*i))
        .astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        for i in range(steps)
    ]
    load_file = output_dir / "truth_load_multiplier.csv"
    _csv(load_file, list(zip(times, load_curve)), "load_multiplier_pu")
    sources = [ReplaySource("LOAD_TRUTH", "timestamp_utc", "UTC", load_file)]
    bindings = [ReplayBinding("LOAD_TRUTH", "load", load_targets, "multiplier", ("load_multiplier_pu",), ("pu",))]
    pv_targets: tuple[str, ...] = ()
    if (feeder_dir.name == "ieee123_pesgm2027"):
        if not re.search(r"(?im)^\s*redirect\s+PESGM2027_P1_PVSystems\.dss\s*(?:!.*)?$", master_text):
            raise B00ExperimentError("MASTER_PV_REDIRECT_MISSING")
        pv_targets = _entities_from_dss(feeder_dir / "PESGM2027_P1_PVSystems.dss", "PVSystem")
        if len(pv_targets) != 10:
            raise B00ExperimentError(f"P1_PV_COUNT_DRIFT: {len(pv_targets)}")
        pv_file = output_dir / "truth_pv_irradiance.csv"
        _csv(pv_file, list(zip(times, pv_curve)), "irradiance_kw_m2")
        sources.append(ReplaySource("PV_TRUTH", "timestamp_utc", "UTC", pv_file))
        bindings.append(ReplayBinding("PV_TRUTH", "pv", pv_targets, "irradiance",
                                      ("irradiance_kw_m2",), ("kW/m2",)))
    spec = ReplaySpec(tuple(sources), tuple(bindings), mode="strict", dt_seconds=dt_seconds,
                      start_time_utc=start, max_steps=steps)
    return spec, {"load_objects": len(load_targets), "pv_objects": len(pv_targets),
                  "truth_files_sha256": {path.name: _sha(path) for path in output_dir.glob("truth_*.csv")},
                  "timestamps_utc": times, "load_multiplier_pu": list(load_curve),
                  "irradiance_kw_m2": list(pv_curve) if pv_targets else None,
                  "profile_type": "SYNTHETIC_DEMONSTRATION_NOT_FIELD_MEASUREMENTS"}


def _plain(raw: Any) -> Any:
    # Python bool subclasses int. Preserve native read-only logical state
    # (RegControl.Enabled, ControlActionsDone) before integer coercion.
    if isinstance(raw, (bool, np.bool_)):
        return bool(raw)
    if isinstance(raw, np.ndarray):
        return [_plain(x) for x in raw.tolist()]
    if isinstance(raw, (tuple, list)):
        return [_plain(x) for x in raw]
    if isinstance(raw, dict):
        return {str(k): _plain(v) for k,v in raw.items()}
    if isinstance(raw, (np.integer, int)):
        return int(raw)
    if isinstance(raw, (np.floating, float)):
        value = float(raw)
        return value if math.isfinite(value) else "NONFINITE"
    if isinstance(raw, (str, bool)) or raw is None:
        return raw
    return repr(raw)


def _leaf(obs: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = obs
    for key in path:
        current = current[key]
    return current


def voltage_summary(obs: dict[str, Any], bindings: tuple[Any, ...]) -> dict[str, Any]:
    values = []
    for binding in bindings:
        if binding.entry.quantity.casefold() != "bus_voltage_pu":
            continue
        raw = np.asarray(_leaf(obs, binding.path), dtype=float).ravel()
        if not np.all(np.isfinite(raw)):
            raise B00ExperimentError("NONFINITE_BUS_VOLTAGE")
        values.extend(float(x) for x in raw)
    if not values:
        raise B00ExperimentError("NO_BUS_VOLTAGE_OBSERVATIONS")
    nonzero = [v for v in values if v > 0.0]
    return {"bus_phase_voltage_count": len(values),
            "min_all_bus_phase_voltage_pu": min(values),
            "max_all_bus_phase_voltage_pu": max(values),
            "nonzero_phase_count": len(nonzero),
            "zero_voltage_phase_count": len(values)-len(nonzero),
            "min_nonzero_bus_phase_voltage_pu": min(nonzero) if nonzero else None,
            "outside_095_105_nonzero_count": sum(v < .95 or v > 1.05 for v in nonzero)}


def _full_state_metric(history_entry: dict[str, Any], entries: dict[str, Any], quantity: str) -> dict[str, Any]:
    full = history_entry.get("full_state")
    if not isinstance(full, dict) or not full:
        return {"status": "NOT_IMPLEMENTED_HISTORY_UNAVAILABLE", "values": {}}
    hits = {}
    failed = {}
    for sid, entry in entries.items():
        if entry.quantity.casefold() != quantity.casefold() or sid not in full:
            continue
        value = full[sid]
        key = entry.native_entity or sid
        if isinstance(value, dict) and "unavailable" in value:
            failed[key] = _plain(value)
        else:
            hits[key] = _plain(value)
    return {"status": "AVAILABLE" if hits and not failed else "PARTIAL" if hits else "NOT_IMPLEMENTED_UNAVAILABLE",
            "values": hits, "unavailable": failed}


def capture_sample(env: OpenDSSSimulator, *, obs: dict[str, Any], info: dict[str, Any], phase: str, native_diagnostics: dict[str, Any] | None = None) -> dict[str, Any]:
    if env.runtime_binding is None or env.semantic_registry is None:
        raise B00ExperimentError("FROZEN_RUNTIME_BINDING_MISSING")
    h = env.history[-1]
    if h.get("requested_action", {}) != {} or h.get("applied_action", {}) != {} or h.get("realized_action", {}) != {}:
        raise B00ExperimentError("B00_EXTERNAL_ACTION_AUDIT_NONEMPTY")
    if info.get("action_audit", []):
        raise B00ExperimentError("B00_NATIVE_ACTION_AUDIT_NONEMPTY")
    solution = info["solution"]
    if not solution["converged"]:
        raise B00ExperimentError("B00_SNAPSHOT_DID_NOT_CONVERGE")
    current_voltage = voltage_summary(obs, env.runtime_binding.observation_bindings)
    entries = env.semantic_registry.entry_by_id()
    sample = {"phase": phase, "time": _plain(info["time"]), "solution": _plain(solution),
            "voltages": current_voltage,
            "transformer_taps": _full_state_metric(h, entries, "transformer_tap_position"),
            "capacitor_states": _full_state_metric(h, entries, "capacitor_state"),
            "control_mode": "NOT_EXPOSED_IN_A05_PUBLIC_SOLUTION",
            "native_enabled_readback": "NOT_EXPOSED_IN_A05_CONTROLLER_CONTEXT",
            "circuit_losses": "NOT_SELECTED_IN_B00I1",
            "switch_states": _full_state_metric(h, entries, "branch_open_state"),
            "exogenous_provenance": _plain(info.get("exogenous", {}).get("replay", {}))}
    if native_diagnostics is not None:
        sample["native_diagnostics"] = _plain(native_diagnostics)
    return sample


def run_feeder(
    *, repo_root: Path, output_root: Path, feeder: str, steps: int = 3,
    seed: int = 511, start: str = "2026-01-01T00:00:00Z", dt_seconds: int = 3600,
    load_curve: tuple[float, ...] = (.75, 1.0, 1.15),
    pv_curve: tuple[float, ...] = (0.0, .8, 1.0),
    history_level: str = "H2", native_diagnostics: bool = False,
) -> dict[str, Any]:
    if feeder not in PRIMARY:
        raise B00ExperimentError("B00_PRIMARY_FEEDER_REQUIRED")
    if steps < 2 or dt_seconds <= 0:
        raise B00ExperimentError("INVALID_B00_EPISODE_LENGTH")
    feeder_dir = repo_root / "experiments" / "pesgm2027" / "feeders" / feeder
    master = feeder_dir / "IEEE123Master.dss"
    if not master.is_file() or output_root.resolve().is_relative_to(repo_root.resolve()):
        raise B00ExperimentError("MISSING_MASTER_OR_OUTPUT_INSIDE_REPO")
    out = output_root / feeder
    if out.exists():
        raise B00ExperimentError(f"B00_OUTPUT_EXISTS_REFUSING_OVERWRITE: {out}")
    out.mkdir(parents=True)
    replay, provenance = make_replay(feeder_dir=feeder_dir, output_dir=out, steps=steps,
                                     start=start, dt_seconds=dt_seconds,
                                     load_curve=load_curve, pv_curve=pv_curve)
    problem = make_problem(feeder)
    env = OpenDSSSimulator(master, problem=problem, exogenous_replay=replay,
                           history_level=HistoryLevel(history_level),
                           inventory_dir=out / "inventory", semantic_registry_dir=out / "semantics",
                           preflight_dir=out / "preflight")
    snapshots: list[dict[str, Any]] = []
    try:
        controller = NativeControlsBaseline()
        assert env.action_space.contains({})
        obs, info = env.reset(seed=seed)
        if len(env.history) != 1:
            raise B00ExperimentError("B00_RESET_HISTORY_MISMATCH")
        inv = env.circuit_inventory
        if inv is None:
            raise B00ExperimentError("B00_INVENTORY_MISSING")
        native_classes = {cls: sum(x.dss_class.casefold()==cls.casefold() for x in inv.native_controls)
                          for cls in ("RegControl", "CapControl", "InvControl", "SwtControl")}
        if native_classes != {"RegControl": 7, "CapControl": 0, "InvControl": 0, "SwtControl": 0}:
            raise B00ExperimentError(f"B00_NATIVE_CONTROL_INVENTORY_DRIFT: {native_classes}")
        contexts = []
        for step in range(steps):
            ctx = env.controller_context(include_static_network=(step==0))
            contexts.append((ctx.decision_time_utc, ctx.electrical_sample_time_utc))
            action = controller.action(context=ctx, action_space=env.action_space)
            if step == 0:
                snapshots.append(capture_sample(env, obs=obs, info=info, phase="reset", native_diagnostics=env.native_diagnostics() if native_diagnostics else None))
            obs, reward, term, truncated, info = env.step(action)
            if (term or truncated) != (step == steps-1):
                raise B00ExperimentError("B00_EPISODE_TERMINATION_DRIFT")
            if reward != 0.0 or not env.observation_space.contains(obs):
                raise B00ExperimentError("B00_UNEXPECTED_REWARD_OR_OBSERVATION")
            if len(env.history) != step+2:
                raise B00ExperimentError("B00_STEP_HISTORY_MISMATCH")
            snapshots.append(capture_sample(env, obs=obs, info=info, phase="step", native_diagnostics=env.native_diagnostics() if native_diagnostics else None))
        if len(snapshots) != steps+1:
            raise B00ExperimentError("B00_SOLVE_COUNT_BOUNDARY_MISMATCH")
        result = {
            "schema": "B00I2.native_diagnostic_campaign.v01" if native_diagnostics else EXPERIMENT_SCHEMA,
            "status": "B00I2_NATIVE_DIAGNOSTICS_RECORDED" if native_diagnostics else "B00I1_NATIVE_PILOT_PASS_TELEMETRY_GAPS_REPORTED",
            "feeder": feeder, "case": "P2_PRE" if PRE_FAULTS[feeder] else "NATIVE_AS_INSTALLED",
            "static_disabled_fault_entities": list(PRE_FAULTS[feeder]),
            "master_sha256": _sha(master), "profile": provenance,
            "problem_spec_sha256": problem.problem_spec_sha256,
            "inventory_semantic_sha256": inv.semantic_sha256,
            "native_controls": native_classes,
            "action_space_empty": True,
            "controller_id": controller.controller_id,
            "solves_expected_from_public_boundary": steps+1,
            "snapshot_count": len(snapshots), "decision_clock_pairs": contexts,
            "snapshots": snapshots,
            "known_gaps": (["STATIC_mode_queue_is_post_solve_only", "tap_steps_are_net_position_proxies",
                             "event_log_may_not_contain_all_control_actions"] if native_diagnostics else
                            ["effective_native_ControlMode_not_exposed", "RegControl_Enabled_not_A04_authorized",
                             "native_regulator_control_queue_not_exposed", "feeder_loss_total_not_selected"]),
            "R01": "OPEN", "R02": "OPEN_MITIGATION_QUALIFIED",
        }
        (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False)+"\n",encoding="utf-8")
        with (out / "summary.csv").open("w",newline="",encoding="utf-8") as stream:
            writer=csv.writer(stream)
            writer.writerow(("phase","completed_steps","sample_time_utc","converged","control_iterations",
                             "feeder_p_kw","feeder_q_kvar","vmin_all_pu","vmax_all_pu","nonzero_vmin_pu","zero_phases","out_of_band_nonzero"))
            for s in snapshots:
                so=s["solution"];v=s["voltages"];t=s["time"]
                writer.writerow((s["phase"],t["completed_steps"],t["electrical_sample_time_utc"],so["converged"],
                    so["control_iterations"],so["total_power_kw"],so["total_power_kvar"],
                    v["min_all_bus_phase_voltage_pu"],v["max_all_bus_phase_voltage_pu"],
                    v["min_nonzero_bus_phase_voltage_pu"],v["zero_voltage_phase_count"],
                    v["outside_095_105_nonzero_count"]))
        return result
    finally:
        env.close()


def _args() -> argparse.Namespace:
    parser=argparse.ArgumentParser(description="B00 read-only-native control time-series pilot")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--feeder", choices=(*PRIMARY,"all"), default="all")
    parser.add_argument("--steps",type=int,default=3)
    parser.add_argument("--seed",type=int,default=511)
    parser.add_argument("--history-level",choices=("H1","H2"),default="H2")
    return parser.parse_args()


def main() -> int:
    args = _args()
    feeders=PRIMARY if args.feeder=="all" else (args.feeder,)
    summary=[]
    for feeder in feeders:
        result=run_feeder(repo_root=args.repo_root.resolve(),output_root=args.output_root.resolve(),
                          feeder=feeder,steps=args.steps,seed=args.seed,history_level=args.history_level)
        print(f"B00_FEEDER={feeder} STATUS={result['status']} SNAPSHOTS={result['snapshot_count']} ",flush=True)
        summary.append({"feeder":feeder,"result_sha256":_sha(args.output_root/feeder/"result.json"),
                        "snapshots":result["snapshot_count"],"status":result["status"]})
    (args.output_root/"campaign_summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("B00_CAMPAIGN=PASS_WITH_EXPLICIT_TELEMETRY_GAPS",flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
