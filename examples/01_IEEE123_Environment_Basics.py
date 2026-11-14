"""Example 01: explore OpenDSSSim and solve repeated, uncontrolled snapshots.

No ProblemSpec, external controller, or load replay. The logical clock changes,
but the input loads are fixed. Example 02 introduces time-varying load data.
"""

# =============================================================================
# 1. IMPORTS
# =============================================================================
import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from opendsssim.environment import EpisodeSpec, OpenDSSSimulator


# =============================================================================
# 2. USER SETTINGS — edit this section only
# =============================================================================
HERE = Path(__file__).resolve().parent
CIRCUIT = HERE / "Input" / "IEEE123_Base" / "IEEE123Master.dss"
OUTPUT = HERE / "Output"
RUN_NAME = "01_basics_demo"
STEPS = 3
SAVE_RESULTS = True
PRINT_DETAILS = False


# =============================================================================
# 3. SET UP INPUT AND OUTPUT LOCATIONS
# =============================================================================
if not CIRCUIT.is_file():
    raise FileNotFoundError(CIRCUIT)

# Even when saving is off, native inventories need a temporary write location.
with TemporaryDirectory(prefix="opendsssim_basics_") as temporary:
    folder = OUTPUT / RUN_NAME if SAVE_RESULTS else Path(temporary)
    if SAVE_RESULTS and folder.exists():
        raise FileExistsError(f"Choose a new RUN_NAME: {folder}")
    folder.mkdir(parents=True, exist_ok=True)

    # ========================================================================
    # 4. CONSTRUCT THE SIMULATOR — direct public API
    # ========================================================================
    env = OpenDSSSimulator(
        network=CIRCUIT,
        backend="altdss",
        problem=None,                    # No controlled problem
        episode_spec=EpisodeSpec(
            start_time_utc="2026-01-01T00:00:00Z",
            dt_seconds=3600,
            max_steps=STEPS,
        ),
        history_level="H1",
        inventory_dir=folder / "Inventory",
        semantic_registry_dir=folder / "SemanticRegistry",
    )

    rows = []
    try:
        # ====================================================================
        # 5. RESET, DISCOVER THE CIRCUIT, AND INSPECT THE AVAILABLE INTERFACES
        # ====================================================================
        observation, info = env.reset(seed=1)
        engine = env.discover_engine()
        circuit = env.discover_circuit()

        print("\nEXAMPLE 01 — OPENDSSSIM ENVIRONMENT BASICS")
        print("Circuit:", circuit.circuit_name)
        print("Buses:", circuit.num_buses, "| Nodes:", circuit.num_nodes)
        print("Gym observation space:", env.observation_space)
        print("Gym action space:", env.action_space)    # Dict({})
        print("Native controls are retained in the feeder.")
        print("Engine public API names:", list(engine.public_api_names))
        print("Inventory:", env.inventory_status, env.inventory_path)
        print("Semantic registry:", env.semantic_registry_status, env.semantic_registry_path)
        print("Initial observation:", observation)

        if PRINT_DETAILS:
            print("First 10 bus names:", [x.name for x in circuit.buses[:10]])
            print("Circuit discovery:", json.dumps(circuit.to_dict(), indent=2, default=str))

        # ====================================================================
        # 6. RUN SNAPSHOTS — no controls, no changes in load input
        # ====================================================================
        for step in range(STEPS):
            action = {}                     # Only valid action with problem=None
            observation, reward, terminated, truncated, info = env.step(action)
            solution = info["solution"]
            diagnostics = env.native_diagnostics()  # Read-only, after AC solve

            row = {
                "step": step + 1,
                "time_utc": info["time"]["electrical_sample_time_utc"],
                "converged": bool(solution["converged"]),
                "total_power_kw": solution["total_power_kw"],
                "total_power_kvar": solution["total_power_kvar"],
                "losses_kw": diagnostics["losses"]["p_kw"],
                "control_iterations": solution["control_iterations"],
            }
            rows.append(row)
            print("Step", row["step"], "| converged", row["converged"],
                  "| total power kW", round(row["total_power_kw"], 2),
                  "| losses kW", round(row["losses_kw"], 2))
            if terminated or truncated:
                break

        print("History records including reset:", len(env.history))

        # ====================================================================
        # 7. OPTIONAL SAVING — CSV summary + public API objects + history
        # ====================================================================
        if SAVE_RESULTS:
            with (folder / "snapshot_summary.csv").open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            for filename, data in {
                "engine.json": engine.to_dict(),
                "circuit.json": circuit.to_dict(),
                "history.json": env.history.records,
                "last_native_diagnostics.json": env.native_diagnostics(),
            }.items():
                (folder / filename).write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")
            print("Outputs saved to:", folder)
        else:
            print("SAVE_RESULTS=False — no permanent output retained")
    finally:
        env.close()
