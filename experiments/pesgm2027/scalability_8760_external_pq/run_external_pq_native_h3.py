"""OpenDSSSim PESGM-2027 V02 external-PQ native-control scalability experiment.

Scientific workload
-------------------
* Three immutable baseline feeders: IEEE-123, European LV, IEEE-8500.
* One exact packaged 8760-hour multiplier CSV is replayed on every feeder.
* A05 ReplayBinding(mode="multiplier") binds the same multiplier to every Load.
  OpenDSSSim therefore applies P_i,t=m_t P_i,0 and Q_i,t=m_t Q_i,0.
* Each load's native baseline power factor remains constant in time.
* Native OpenDSS controls retain authority; external electrical action is empty.
* HistoryLevel.H3 is requested. Each OpenDSSSim H3 record is immediately streamed
  to gzip JSONL and then RuntimeHistory.clear() is called, bounding Python retention.
* The runner never writes directly to AltDSS.

The full 8760 campaign should only be launched after the H3 pilot is reviewed because
H3 intentionally reads the complete state registry at every solve.
"""
from __future__ import annotations

import argparse
import csv
import ctypes
from ctypes import wintypes
from collections import Counter
from datetime import datetime, timezone
import gzip
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import platform
import shutil
import statistics
import sys
import time
from typing import Any, Mapping

# Repository-local import bootstrap for direct execution from a setuptools src/ layout.
# This mirrors OpenDSSSim's standalone validation scripts and does not modify the
# Python environment or require an editable install.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_REPO_SRC = _REPO_ROOT / "src"
if str(_REPO_SRC) not in sys.path:
    sys.path.insert(0, str(_REPO_SRC))

import numpy as np

from opendsssim.controllers.baselines import NativeControlsBaseline
from opendsssim.environment import (
    OpenDSSSimulator,
    ReplayBinding,
    ReplaySource,
    ReplaySpec,
)
from opendsssim.problem import (
    ActionSpec,
    ControlAuthorityMode,
    ControlAuthoritySpec,
    ObservationSpec,
    ProblemSpec,
    RegistryKind,
    SelectionGroup,
    SemanticQuery,
)
from opendsssim.runtime import ExecutionProfile, HistoryLevel


SCHEMA = "OpenDSSSim.PESGM2027.Scalability8760.ExternalPQNativeH3.v02"
DEFAULT_PROFILE = "truth_load_multiplier_8760.csv"

FEEDERS = {
    "ieee123_base": {
        "master": "IEEE123Master.dss",
        "scale_gate": ("num_nodes", 123),
    },
    "ieee906_european_lv_base": {
        "master": "Master.dss",
        "scale_gate": ("num_buses", 123),
    },
    "ieee8500_base": {
        "master": "Master.dss",
        "scale_gate": ("num_nodes", 8000),
    },
}


class ExperimentError(RuntimeError):
    pass


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest().upper()


def tree_digest(root: Path) -> str:
    h = sha256()
    for p in sorted(
        (x for x in root.rglob("*") if x.is_file()),
        key=lambda x: x.relative_to(root).as_posix().casefold(),
    ):
        data = p.read_bytes()
        h.update(p.relative_to(root).as_posix().encode("utf-8"))
        h.update(b"\0")
        h.update(str(len(data)).encode("ascii"))
        h.update(b"\0")
        h.update(sha256(data).hexdigest().upper().encode("ascii"))
        h.update(b"\n")
    return h.hexdigest().upper()


def jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, complex):
        return {"real": float(value.real), "imag": float(value.imag)}
    if isinstance(value, np.ndarray):
        return [jsonable(x) for x in value.tolist()]
    if isinstance(value, np.generic):
        return jsonable(value.item())
    if isinstance(value, Mapping):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [jsonable(x) for x in value]
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    if hasattr(value, "value") and isinstance(value.value, (str, int, float, bool)):
        return value.value
    return str(value)


class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]


def memory_snapshot() -> dict[str, int | None]:
    if os.name != "nt":
        return {"rss_bytes": None, "peak_rss_bytes": None, "private_bytes": None}
    try:
        c = PROCESS_MEMORY_COUNTERS_EX()
        c.cb = ctypes.sizeof(c)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        ok = ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(c), c.cb)
        if not ok:
            raise OSError("GetProcessMemoryInfo failed")
        return {
            "rss_bytes": int(c.WorkingSetSize),
            "peak_rss_bytes": int(c.PeakWorkingSetSize),
            "private_bytes": int(c.PrivateUsage),
        }
    except Exception:
        return {"rss_bytes": None, "peak_rss_bytes": None, "private_bytes": None}


def percentile(values: list[float], q: float) -> float:
    a = sorted(values)
    if len(a) == 1:
        return float(a[0])
    p = (len(a) - 1) * q
    lo = math.floor(p)
    hi = math.ceil(p)
    if lo == hi:
        return float(a[lo])
    f = p - lo
    return float(a[lo] * (1.0 - f) + a[hi] * f)


def stats(values: list[float]) -> dict[str, float | int]:
    if not values:
        raise ExperimentError("EMPTY_METRIC_VECTOR")
    return {
        "count": len(values),
        "sum": float(sum(values)),
        "mean": float(statistics.fmean(values)),
        "median": float(statistics.median(values)),
        "std": float(statistics.pstdev(values)) if len(values) > 1 else 0.0,
        "min": float(min(values)),
        "p95": percentile(values, 0.95),
        "p99": percentile(values, 0.99),
        "max": float(max(values)),
    }


def read_profile(path: Path) -> tuple[list[dict[str, str]], list[float]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    required = {
        "timestamp_utc",
        "day_index",
        "hour_of_day",
        "daily_base_multiplier_pu",
        "gaussian_noise_pu",
        "load_multiplier_pu",
    }
    if len(rows) != 8760 or not rows or not required.issubset(rows[0]):
        raise ExperimentError("INVALID_8760_PROFILE")
    multipliers = [float(x["load_multiplier_pu"]) for x in rows]
    if any(not math.isfinite(x) or x < 0 for x in multipliers):
        raise ExperimentError("INVALID_PROFILE_MULTIPLIER")
    return rows, multipliers


def make_problem(feeder: str) -> ProblemSpec:
    return ProblemSpec.create(
        "pesgm2027-scalability8760-external-pq-native", "2",
        observations=ObservationSpec(
            groups=(
                SelectionGroup(
                    "native_timeseries",
                    (
                        SemanticQuery(
                            RegistryKind.STATE,
                            quantity="solution_converged",
                        ),
                        SemanticQuery(
                            RegistryKind.STATE,
                            quantity="bus_voltage_pu",
                        ),
                    ),
                ),
            ),
        ),
        actions=ActionSpec(),
        control_authority=ControlAuthoritySpec(
            mode=ControlAuthorityMode.NATIVE
        ),
        metadata={
            "benchmark": "SCALABILITY_8760_EXTERNAL_PQ",
            "feeder": feeder,
            "load_truth": "A05_REPLAY_MULTIPLIER",
            "constant_pf": "NATIVE_BASELINE_PER_LOAD",
            "history": "H3_STREAMED_GZIP_JSONL",
            "weather": "NOT_APPLIED",
            "external_actions": "NONE",
        },
    )


def copy_feeder(
    repo_root: Path,
    feeder: str,
    run_dir: Path,
    max_iterations: int,
) -> tuple[Path, dict[str, Any]]:
    source = repo_root / "experiments" / "pesgm2027" / "feeders" / feeder
    cfg = FEEDERS[feeder]
    master = source / cfg["master"]
    if not master.is_file():
        raise ExperimentError(f"MISSING_MASTER: {master}")

    source_before = tree_digest(source)
    work = run_dir / "working_feeder"
    t0 = time.perf_counter_ns()
    shutil.copytree(source, work)
    copy_ms = (time.perf_counter_ns() - t0) / 1e6

    wrapper = work / "__OpenDSSSim_ScalabilityV02_Master.dss"
    wrapper.write_text(
        "! Generated experiment entrypoint; baseline feeder files are unchanged.\n"
        f'Redirect "{cfg["master"]}"\n'
        f"Set MaxIterations={int(max_iterations)}\n",
        encoding="utf-8",
    )

    if tree_digest(source) != source_before:
        raise ExperimentError(f"REPOSITORY_FEEDER_MUTATED_DURING_COPY: {feeder}")

    return wrapper, {
        "repository_source": str(source),
        "repository_source_tree_sha256": source_before,
        "working_copy_ms": copy_ms,
        "wrapper": wrapper.name,
        "max_iterations": int(max_iterations),
    }


def discover_loads(
    wrapper: Path,
    problem: ProblemSpec,
    artifact_root: Path,
) -> tuple[tuple[str, ...], dict[str, Any]]:
    t0 = time.perf_counter_ns()
    env = OpenDSSSimulator(
        wrapper,
        source_root=wrapper.parent,
        problem=problem,
        history_level=HistoryLevel.H0,
        execution_profile=ExecutionProfile.STANDARD,
        inventory_dir=artifact_root / "inventory",
        semantic_registry_dir=artifact_root / "semantics",
        preflight_dir=artifact_root / "preflight",
    )
    construct_ms = (time.perf_counter_ns() - t0) / 1e6
    try:
        inv = env.circuit_inventory
        if inv is None:
            raise ExperimentError("DISCOVERY_INVENTORY_MISSING")
        loads = tuple(
            sorted(
                (
                    obj.full_name
                    for obj in inv.objects
                    if obj.dss_class.casefold() == "load"
                ),
                key=str.casefold,
            )
        )
        if not loads:
            raise ExperimentError("NO_LOAD_OBJECTS_DISCOVERED")
        counts = {
            "num_buses": int(inv.num_buses),
            "num_nodes": int(inv.num_nodes),
            "num_circuit_elements": int(inv.num_circuit_elements),
            "num_load_objects": len(loads),
            "native_control_counts": dict(
                sorted(
                    Counter(
                        str(x.dss_class)
                        for x in inv.native_controls
                    ).items(),
                    key=lambda kv: kv[0].casefold(),
                )
            ),
            "inventory_semantic_sha256": inv.semantic_sha256,
            "source_tree_sha256": inv.source_tree_sha256,
        }
        return loads, {
            "discovery_env_construct_ms": construct_ms,
            "counts": counts,
        }
    finally:
        env.close()


def make_replay(
    profile: Path,
    load_targets: tuple[str, ...],
    steps: int,
) -> ReplaySpec:
    return ReplaySpec(
        sources=(
            ReplaySource(
                "LOAD_TRUTH_8760",
                "timestamp_utc",
                "UTC",
                profile,
            ),
        ),
        bindings=(
            ReplayBinding(
                "LOAD_TRUTH_8760",
                "load",
                load_targets,
                "multiplier",
                ("load_multiplier_pu",),
                ("pu",),
            ),
        ),
        mode="strict",
        dt_seconds=3600,
        start_time_utc="2026-01-01T00:00:00Z",
        max_steps=steps,
    )


def write_h3_record(
    stream: Any,
    record: Mapping[str, Any],
) -> tuple[float, int]:
    t0 = time.perf_counter_ns()
    text = json.dumps(
        jsonable(record),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    stream.write(text)
    stream.write("\n")
    stream.flush()
    elapsed_ms = (time.perf_counter_ns() - t0) / 1e6
    return elapsed_ms, len(text.encode("utf-8")) + 1


def run_one(
    repo_root: Path,
    output_root: Path,
    profile_source: Path,
    feeder: str,
    steps: int,
    repetition: int,
    seed: int,
    max_iterations: int,
    warmup_steps: int,
) -> dict[str, Any]:
    run_dir = output_root / feeder / f"rep_{repetition:02d}"
    if run_dir.exists():
        raise ExperimentError(f"OUTPUT_EXISTS: {run_dir}")
    run_dir.mkdir(parents=True)

    overall_start = time.perf_counter_ns()
    source_repo = (
        repo_root / "experiments" / "pesgm2027" / "feeders" / feeder
    )
    repo_digest_before = tree_digest(source_repo)

    wrapper, source_info = copy_feeder(
        repo_root, feeder, run_dir, max_iterations
    )

    t0 = time.perf_counter_ns()
    profile = run_dir / "truth_load_multiplier_8760.csv"
    shutil.copy2(profile_source, profile)
    profile_copy_ms = (time.perf_counter_ns() - t0) / 1e6
    profile_rows, multipliers = read_profile(profile)

    t0 = time.perf_counter_ns()
    problem = make_problem(feeder)
    problem_build_ms = (time.perf_counter_ns() - t0) / 1e6

    artifact_root = run_dir / "runtime_artifacts"
    loads, discovery = discover_loads(
        wrapper, problem, artifact_root
    )

    t0 = time.perf_counter_ns()
    replay = make_replay(profile, loads, steps)
    replay_build_ms = (time.perf_counter_ns() - t0) / 1e6

    t0 = time.perf_counter_ns()
    env = OpenDSSSimulator(
        wrapper,
        source_root=wrapper.parent,
        problem=problem,
        exogenous_replay=replay,
        history_level=HistoryLevel.H3,
        execution_profile=ExecutionProfile.STANDARD,
        inventory_dir=artifact_root / "inventory",
        semantic_registry_dir=artifact_root / "semantics",
        preflight_dir=artifact_root / "preflight",
    )
    final_env_construct_ms = (time.perf_counter_ns() - t0) / 1e6

    controller = NativeControlsBaseline()
    timing_rows: list[dict[str, Any]] = []
    debug_path = run_dir / "debug_history_H3.jsonl.gz"
    uncompressed_debug_bytes = 0
    debug_records = 0

    try:
        with gzip.open(debug_path, "wt", encoding="utf-8", compresslevel=6) as debug:
            t0 = time.perf_counter_ns()
            obs, info = env.reset(seed=seed)
            reset_wall_ms = (time.perf_counter_ns() - t0) / 1e6

            if len(env.history) != 1:
                raise ExperimentError("RESET_H3_HISTORY_COUNT_MISMATCH")
            reset_record = env.history[-1]
            reset_debug_ms, reset_debug_bytes = write_h3_record(
                debug, reset_record
            )
            uncompressed_debug_bytes += reset_debug_bytes
            debug_records += 1
            env.history.clear()

            if not env.action_space.contains({}):
                raise ExperimentError("NATIVE_EMPTY_ACTION_NOT_AUTHORIZED")
            if not env.observation_space.contains(obs):
                raise ExperimentError("RESET_OBSERVATION_OUTSIDE_SPACE")

            reset_solution = dict(info["solution"])
            if not bool(reset_solution["converged"]):
                raise ExperimentError("RESET_NOT_CONVERGED")

            # First full static controller context is pre-simulation/setup.
            t0 = time.perf_counter_ns()
            static_context = env.controller_context(
                include_static_network=True
            )
            static_context_ms = (time.perf_counter_ns() - t0) / 1e6

            t0 = time.perf_counter_ns()
            static_action = controller.action(
                context=static_context,
                action_space=env.action_space,
            )
            static_action_ms = (time.perf_counter_ns() - t0) / 1e6
            if static_action != {}:
                raise ExperimentError("NATIVE_CONTROLLER_NONEMPTY_ACTION")

            for step_index in range(1, steps + 1):
                loop_start = time.perf_counter_ns()
                cpu_start = time.process_time_ns()

                t0 = time.perf_counter_ns()
                context = env.controller_context(
                    include_static_network=False
                )
                context_ms = (time.perf_counter_ns() - t0) / 1e6

                t0 = time.perf_counter_ns()
                action = controller.action(
                    context=context,
                    action_space=env.action_space,
                )
                action_ms = (time.perf_counter_ns() - t0) / 1e6

                t0 = time.perf_counter_ns()
                obs, reward, terminated, truncated, info = env.step(action)
                env_step_ms = (time.perf_counter_ns() - t0) / 1e6

                if len(env.history) != 1:
                    raise ExperimentError(
                        f"H3_STREAMING_HISTORY_COUNT_MISMATCH: {len(env.history)}"
                    )

                h3 = env.history[-1]
                replay_info = (
                    h3.get("info", {})
                    .get("exogenous", {})
                    .get("replay", {})
                )
                expected_logical = step_index - 1
                if replay_info.get("logical_index") != expected_logical:
                    raise ExperimentError(
                        "REPLAY_LOGICAL_INDEX_DRIFT: "
                        f"expected={expected_logical} "
                        f"actual={replay_info.get('logical_index')}"
                    )

                debug_ms, debug_bytes = write_h3_record(debug, h3)
                uncompressed_debug_bytes += debug_bytes
                debug_records += 1
                env.history.clear()

                solution = dict(info["solution"])
                if not bool(solution["converged"]):
                    raise ExperimentError(
                        f"NONCONVERGENCE: feeder={feeder} step={step_index}"
                    )
                if reward != 0.0:
                    raise ExperimentError(
                        f"NATIVE_REWARD_DRIFT: {reward}"
                    )
                if not env.observation_space.contains(obs):
                    raise ExperimentError("OBSERVATION_OUTSIDE_SPACE")

                expected_end = step_index == steps
                if bool(terminated or truncated) != expected_end:
                    raise ExperimentError(
                        "EPISODE_END_DRIFT: "
                        f"step={step_index} "
                        f"terminated={terminated} truncated={truncated}"
                    )

                engine_ms = (
                    1000.0 * float(solution["process_time_s"])
                )
                mem = memory_snapshot()
                total_loop_ms = (
                    time.perf_counter_ns() - loop_start
                ) / 1e6
                cpu_ms = (
                    time.process_time_ns() - cpu_start
                ) / 1e6

                timing_rows.append(
                    {
                        "step_index": step_index,
                        "profile_row_index": expected_logical,
                        "timestamp_utc": profile_rows[
                            expected_logical
                        ]["timestamp_utc"],
                        "load_multiplier_pu": multipliers[
                            expected_logical
                        ],
                        "controller_context_ms": context_ms,
                        "controller_action_ms": action_ms,
                        "env_step_wall_ms": env_step_ms,
                        "engine_process_ms": engine_ms,
                        "framework_plus_H3_ms": (
                            env_step_ms - engine_ms
                        ),
                        "debug_H3_serialize_gzip_ms": debug_ms,
                        "total_loop_wall_ms": total_loop_ms,
                        "total_loop_cpu_ms": cpu_ms,
                        "iterations": int(solution["iterations"]),
                        "total_iterations": int(
                            solution["total_iterations"]
                        ),
                        "control_iterations": int(
                            solution["control_iterations"]
                        ),
                        "converged": bool(solution["converged"]),
                        "feeder_p_kw": float(
                            solution["total_power_kw"]
                        ),
                        "feeder_q_kvar": float(
                            solution["total_power_kvar"]
                        ),
                        "rss_bytes": mem["rss_bytes"],
                        "peak_rss_bytes": mem[
                            "peak_rss_bytes"
                        ],
                        "private_bytes": mem["private_bytes"],
                    }
                )

            close_start = time.perf_counter_ns()
            env.close()
            env_close_ms = (
                time.perf_counter_ns() - close_start
            ) / 1e6
    finally:
        try:
            env.close()
        except Exception:
            pass

    repo_digest_after = tree_digest(source_repo)
    if repo_digest_after != repo_digest_before:
        raise ExperimentError(
            f"REPOSITORY_BASELINE_MUTATED: {feeder}"
        )

    timings_path = run_dir / "timings.csv"
    with timings_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=list(timing_rows[0].keys()),
        )
        w.writeheader()
        w.writerows(timing_rows)

    metric_names = (
        "controller_context_ms",
        "controller_action_ms",
        "env_step_wall_ms",
        "engine_process_ms",
        "framework_plus_H3_ms",
        "debug_H3_serialize_gzip_ms",
        "total_loop_wall_ms",
    )
    steady = timing_rows[
        min(max(warmup_steps, 0), len(timing_rows)):
    ]
    timing_summary = {
        "all_steps": {
            name: stats(
                [float(x[name]) for x in timing_rows]
            )
            for name in metric_names
        },
        "steady_after_warmup": {
            "excluded_first_steps": min(
                max(warmup_steps, 0),
                len(timing_rows),
            ),
            "metrics": {
                name: stats(
                    [float(x[name]) for x in steady]
                )
                for name in metric_names
            } if steady else {},
        },
    }

    compressed_bytes = debug_path.stat().st_size
    projected_records = 8761
    projected_h3_gzip_bytes = (
        compressed_bytes / debug_records * projected_records
        if debug_records
        else None
    )
    elapsed_ms = (
        time.perf_counter_ns() - overall_start
    ) / 1e6
    projected_full_wall_ms = (
        elapsed_ms / steps * 8760
        if steps > 0
        else None
    )

    scale_field, threshold = FEEDERS[feeder]["scale_gate"]
    counts = discovery["counts"]
    if int(counts[scale_field]) <= int(threshold):
        raise ExperimentError(
            f"SCALE_GATE_FAILED: {scale_field}"
        )

    summary = {
        "schema": SCHEMA,
        "status": "PASS",
        "feeder": feeder,
        "repetition": repetition,
        "workload": {
            "steps": steps,
            "dt_seconds": 3600,
            "history_level": "H3",
            "execution_profile": "STANDARD",
            "native_controls": True,
            "external_controller_action": False,
            "external_load_pq": True,
            "load_binding_mode": "multiplier",
            "constant_pf": "native baseline per load",
            "weather_actuation": False,
        },
        "profile": {
            "path": str(profile),
            "sha256": sha_file(profile),
            "rows_total": len(profile_rows),
            "used_rows": steps,
            "seed": 8760,
            "gaussian_sigma_pu": 0.02,
        },
        "source": {
            **source_info,
            "repository_source_tree_sha256_after": repo_digest_after,
            "repository_source_mutated": False,
        },
        "circuit": counts,
        "problem": {
            "problem_spec_sha256": problem.problem_spec_sha256,
            "controller_id": controller.controller_id,
            "action_space_empty": True,
            "observation_quantities": [
                "solution_converged",
                "bus_voltage_pu",
            ],
        },
        "pre_simulation_timing_ms": {
            "working_feeder_copy": source_info[
                "working_copy_ms"
            ],
            "profile_copy": profile_copy_ms,
            "problem_spec_build": problem_build_ms,
            "discovery_env_construct": discovery[
                "discovery_env_construct_ms"
            ],
            "replay_spec_build": replay_build_ms,
            "final_env_construct": final_env_construct_ms,
            "reset_total": reset_wall_ms,
            "reset_engine_process": (
                1000.0 * float(
                    reset_solution["process_time_s"]
                )
            ),
            "reset_H3_serialize_gzip": reset_debug_ms,
            "static_controller_context": static_context_ms,
            "static_controller_action": static_action_ms,
        },
        "timing": timing_summary,
        "debug_history": {
            "format": "gzip-jsonl",
            "path": str(debug_path),
            "records_written": debug_records,
            "uncompressed_json_bytes": uncompressed_debug_bytes,
            "compressed_bytes": compressed_bytes,
            "linear_projected_8761_record_compressed_bytes": (
                projected_h3_gzip_bytes
            ),
            "projection_note": (
                "Rough linear pilot projection only; gzip compression "
                "ratio may change over a full run."
            ),
            "streamed_and_history_cleared_each_record": True,
        },
        "pilot_projection": {
            "observed_run_wall_ms": elapsed_ms,
            "rough_linear_projected_8760_step_wall_ms": (
                projected_full_wall_ms
            ),
        },
        "final_memory": memory_snapshot(),
        "env_close_ms": env_close_ms,
        "created_utc": now_utc(),
    }

    (run_dir / "summary.json").write_text(
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return summary


def write_campaign_summary(
    output_root: Path,
    summaries: list[dict[str, Any]],
) -> None:
    rows = []
    for s in summaries:
        tm = s["timing"]["all_steps"]
        rows.append(
            {
                "feeder": s["feeder"],
                "repetition": s["repetition"],
                "num_buses": s["circuit"]["num_buses"],
                "num_nodes": s["circuit"]["num_nodes"],
                "num_circuit_elements": s[
                    "circuit"
                ]["num_circuit_elements"],
                "num_load_objects": s[
                    "circuit"
                ]["num_load_objects"],
                "env_step_median_ms": tm[
                    "env_step_wall_ms"
                ]["median"],
                "env_step_p95_ms": tm[
                    "env_step_wall_ms"
                ]["p95"],
                "engine_median_ms": tm[
                    "engine_process_ms"
                ]["median"],
                "framework_plus_H3_median_ms": tm[
                    "framework_plus_H3_ms"
                ]["median"],
                "debug_serialize_median_ms": tm[
                    "debug_H3_serialize_gzip_ms"
                ]["median"],
                "projected_H3_gzip_bytes_8761": s[
                    "debug_history"
                ][
                    "linear_projected_8761_record_compressed_bytes"
                ],
            }
        )

    with (output_root / "campaign_summary.csv").open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        w = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys()),
        )
        w.writeheader()
        w.writerows(rows)

    (output_root / "campaign_summary.json").write_text(
        json.dumps(
            {
                "schema": SCHEMA + ".campaign",
                "status": "PASS",
                "summaries": rows,
                "repository_mutated": False,
            },
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def preflight(
    repo_root: Path,
    profile: Path,
) -> dict[str, Any]:
    profile_rows, multipliers = read_profile(profile)
    result = {
        "schema": SCHEMA + ".preflight",
        "status": "PASS",
        "profile": {
            "sha256": sha_file(profile),
            "rows": len(profile_rows),
            "min": min(multipliers),
            "max": max(multipliers),
            "mean": statistics.fmean(multipliers),
        },
        "feeders": [],
        "repository_mutated": False,
    }

    preflight_root = (
        Path(os.environ.get("TEMP", "."))
        / "OpenDSSSim_Scalability8760_V02_Preflight"
    )
    shutil.rmtree(preflight_root, ignore_errors=True)
    preflight_root.mkdir(parents=True)

    for feeder in FEEDERS:
        out = preflight_root / feeder
        out.mkdir()
        wrapper, source_info = copy_feeder(
            repo_root, feeder, out, 100
        )
        problem = make_problem(feeder)
        loads, discovery = discover_loads(
            wrapper,
            problem,
            out / "artifacts",
        )
        result["feeders"].append(
            {
                "feeder": feeder,
                **discovery["counts"],
                "load_targets": len(loads),
                "source_sha256": source_info[
                    "repository_source_tree_sha256"
                ],
            }
        )
    shutil.rmtree(preflight_root, ignore_errors=True)
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", type=Path, required=True)
    p.add_argument("--output-root", type=Path)
    p.add_argument("--profile", type=Path)
    p.add_argument("--steps", type=int, default=8760)
    p.add_argument("--repetitions", type=int, default=1)
    p.add_argument("--seed", type=int, default=8760)
    p.add_argument("--warmup-steps", type=int, default=24)
    p.add_argument("--max-iterations", type=int, default=100)
    p.add_argument(
        "--feeders",
        default=",".join(FEEDERS),
    )
    p.add_argument("--preflight-only", action="store_true")
    args = p.parse_args()

    repo = args.repo_root.resolve()
    if not (repo / "pyproject.toml").is_file():
        raise ExperimentError("INVALID_REPO_ROOT")

    default_profile = (
        repo
        / "experiments"
        / "pesgm2027"
        / "scalability_8760_external_pq"
        / DEFAULT_PROFILE
    )
    profile = (
        default_profile
        if args.profile is None
        else args.profile.resolve()
    )
    if not profile.is_file():
        raise ExperimentError(f"PROFILE_MISSING: {profile}")

    if args.preflight_only:
        doc = preflight(repo, profile)
        print(json.dumps(doc, indent=2))
        return 0

    if args.output_root is None:
        raise ExperimentError("--output-root is required")
    output_root = args.output_root.resolve()
    if output_root.is_relative_to(repo):
        raise ExperimentError(
            "OUTPUT_ROOT_MUST_BE_OUTSIDE_REPOSITORY"
        )
    if output_root.exists():
        raise ExperimentError(
            f"OUTPUT_ROOT_EXISTS: {output_root}"
        )
    output_root.mkdir(parents=True)

    feeders = [
        x.strip()
        for x in args.feeders.split(",")
        if x.strip()
    ]
    unknown = sorted(set(feeders).difference(FEEDERS))
    if unknown:
        raise ExperimentError(
            f"UNKNOWN_FEEDERS: {unknown}"
        )
    if not (1 <= args.steps <= 8760):
        raise ExperimentError(
            "STEPS_MUST_BE_IN_1_TO_8760"
        )
    if args.repetitions <= 0:
        raise ExperimentError(
            "REPETITIONS_MUST_BE_POSITIVE"
        )

    summaries = []
    campaign_start = time.perf_counter_ns()
    for rep in range(1, args.repetitions + 1):
        for feeder in feeders:
            print(
                f"[RUN] {feeder} rep={rep} "
                f"steps={args.steps} H3 external-PQ",
                flush=True,
            )
            s = run_one(
                repo,
                output_root,
                profile,
                feeder,
                args.steps,
                rep,
                args.seed + rep - 1,
                args.max_iterations,
                args.warmup_steps,
            )
            summaries.append(s)
            print(
                f"[PASS] {feeder} "
                f"buses={s['circuit']['num_buses']} "
                f"nodes={s['circuit']['num_nodes']} "
                f"loads={s['circuit']['num_load_objects']} "
                f"median_step_ms="
                f"{s['timing']['all_steps']['env_step_wall_ms']['median']:.6f}",
                flush=True,
            )

    write_campaign_summary(output_root, summaries)
    campaign_wall_ms = (
        time.perf_counter_ns() - campaign_start
    ) / 1e6
    print(
        f"CAMPAIGN_STATUS=PASS "
        f"CAMPAIGN_WALL_MS={campaign_wall_ms:.3f}"
    )
    print(f"OUTPUT_ROOT={output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
