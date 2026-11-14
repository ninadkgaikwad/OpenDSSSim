"""Example 02: genuine hourly IEEE-123 simulation, WITHOUT an external controller.

Input/ holds the unchanged feeder, a 24-hour synthetic multiplier CSV, and
91 explicit Load.* targets. ReplaySpec applies these changing loads through
OpenDSSSim's physical exogenous-input mechanism. The only Gym action is {}.
"""

# =============================================================================
# 1. IMPORTS
# =============================================================================
import csv
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from opendsssim.environment import (
    OpenDSSSimulator, ReplaySource, ReplayBinding, ReplaySpec,
)


# =============================================================================
# 2. USER SETTINGS — try changing these values
# =============================================================================
HERE = Path(__file__).resolve().parent
INPUT = HERE / "Input"
OUTPUT = HERE / "Output"
CIRCUIT = INPUT / "IEEE123_Base" / "IEEE123Master.dss"
LOAD_PROFILE = INPUT / "synthetic_hourly_load_multiplier.csv"
LOAD_TARGETS = INPUT / "ieee123_load_targets.csv"
RUN_NAME = "02_uncontrolled_24h"
STEPS = 24                         # Hourly control-free environment steps
SAVE_RESULTS = True                 # False: print only; temp native metadata
PRINT_EACH_HOUR = True
SAVE_NATIVE_DIAGNOSTICS = True       # Read-only snapshots: losses / regulators


# =============================================================================
# 3. READ INPUT FILES (both physical data and target binding are explicit)
# =============================================================================
for path in (CIRCUIT, LOAD_PROFILE, LOAD_TARGETS):
    if not path.is_file():
        raise FileNotFoundError(path)

with LOAD_TARGETS.open(newline="", encoding="utf-8") as f:
    targets = tuple(row["native_load"] for row in csv.DictReader(f))
if not targets:
    raise ValueError("No native loads selected")

# ReplaySpec, not EpisodeSpec, owns the time grid when CSV replay is used.
# multiplier (pu) scales each load's baseline kW and kvar together.
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
    mode="strict",                    # Never silently repeat missing data
    dt_seconds=3600,
    start_time_utc="2026-01-01T00:00:00Z",
    max_steps=STEPS,
)


# =============================================================================
# 4. CONSTRUCT THE SIMULATOR AND CONFIGURE OUTPUTS
# =============================================================================
with TemporaryDirectory(prefix="opendsssim_replay_") as temporary:
    folder = OUTPUT / RUN_NAME if SAVE_RESULTS else Path(temporary)
    if SAVE_RESULTS and folder.exists():
        raise FileExistsError(f"Choose a new RUN_NAME: {folder}")
    folder.mkdir(parents=True, exist_ok=True)

    env = OpenDSSSimulator(
        network=CIRCUIT,
        backend="altdss",
        problem=None,                   # NO ProblemSpec
        exogenous_replay=replay,         # Qualified physical input contract
        history_level="H1",
        inventory_dir=folder / "Inventory",
        semantic_registry_dir=folder / "SemanticRegistry",
    )

    rows = []
    native_snapshots = []
    try:
        # ====================================================================
        # 5. RESET: DISCOVER WHAT IS AVAILABLE BEFORE STEPPING
        # ====================================================================
        observation, info = env.reset(seed=1)
        circuit = env.discover_circuit()

        print("\nEXAMPLE 02 — IEEE-123 UNCONTROLLED HOURLY TIME SERIES")
        print("Circuit:", circuit.circuit_name, "| Buses:", circuit.num_buses)
        print("Physical replay targets:", len(targets), "load objects")
        print("Observation space:", env.observation_space)   # Convergence only
        print("Action space:", env.action_space)           # Empty Dict({})
        print("Reset converged:", info["solution"]["converged"])
        print("Replay source identity:", info["exogenous"]["replay"]["replay_sha256"])
        print("Note: native IEEE-123 controls still operate inside AltDSS.")

        # ====================================================================
        # 6. RUN THE HOURLY PHYSICAL INPUT SERIES THROUGH env.step({})
        # ====================================================================
        # IMPORTANT TIME SEMANTICS:
        # reset solves sample 0. Step 1 solves sample 0 again, at the same
        # electrical sample time; Step 2 solves sample 1; ... Step 24 sample 23.
        # There are 24 environment steps, plus one reset AC snapshot.
        for step in range(1, STEPS + 1):
            action = {}                 # NO external controller action
            observation, reward, terminated, truncated, info = env.step(action)
            solution = info["solution"]
            diagnostic = env.native_diagnostics()
            replay_info = info["exogenous"]["replay"]["sources"][0]

            row = {
                "step": step,
                "electrical_time_utc": info["time"]["electrical_sample_time_utc"],
                "replay_sample_index": replay_info["canonical_index"],
                "converged": bool(solution["converged"]),
                "total_power_kw": solution["total_power_kw"],
                "total_power_kvar": solution["total_power_kvar"],
                "losses_kw": diagnostic["losses"]["p_kw"],
                "losses_kvar": diagnostic["losses"]["q_kvar"],
                "iterations": solution["iterations"],
                "control_iterations": solution["control_iterations"],
            }
            rows.append(row)
            if SAVE_RESULTS and SAVE_NATIVE_DIAGNOSTICS:
                native_snapshots.append({"step": step, "diagnostics": diagnostic})
            if PRINT_EACH_HOUR:
                print(f"Hour {step:02d} | input row {row['replay_sample_index']:02d} | "
                      f"AC={row['converged']} | P={row['total_power_kw']:.1f} kW | "
                      f"losses={row['losses_kw']:.2f} kW | "
                      f"native control iterations={row['control_iterations']}")
            if terminated or truncated:
                break

        # ====================================================================
        # 7. VIEW HISTORY AND SAVE REPRODUCIBLE OUTPUTS (OPTIONAL)
        # ====================================================================
        print("Completed environment steps:", len(rows))
        print("Native solves including reset:", len(env.history))
        print("Last solution converged:", env.last_result.converged)

        if SAVE_RESULTS:
            with (folder / "hourly_results.csv").open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            settings = {
                "circuit": str(CIRCUIT), "profile": str(LOAD_PROFILE),
                "load_targets": len(targets), "steps": STEPS,
                "no_problem_spec": True, "no_external_controller": True,
                "profile_sha256": hashlib.sha256(LOAD_PROFILE.read_bytes()).hexdigest(),
                "target_sha256": hashlib.sha256(LOAD_TARGETS.read_bytes()).hexdigest(),
                "input_profile_is_synthetic": True,
            }
            for filename, data in {
                "run_settings.json": settings,
                "history.json": env.history.records,
                "last_native_diagnostics.json": env.native_diagnostics(),
                **({"native_diagnostics_per_step.json": native_snapshots}
                   if SAVE_NATIVE_DIAGNOSTICS else {}),
            }.items():
                (folder / filename).write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")
            print("Saved outputs to:", folder)
            print("Next: 03_Inspect_Saved_Results.py")
        else:
            print("SAVE_RESULTS=False — no permanent output retained")
    finally:
        env.close()
