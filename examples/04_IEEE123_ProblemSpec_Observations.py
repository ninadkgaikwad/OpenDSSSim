"""EXAMPLE 04 - ProblemSpec: request electrical measurements without a controller.

PREAMBLE
========
Aim
    Teach how an authored ProblemSpec selects native semantic quantities and
    how OpenDSSSim converts them into a deterministic Gymnasium observation
    space. This is a *controlled observation interface*, not a controller.

What you will learn
    1. Write ObservationSpec -> SelectionGroup -> SemanticQuery.
    2. Understand STATE registry, native classes, quantities, and cardinality.
    3. Inspect authored / resolved contracts and compiled Gym spaces.
    4. Read the nested observations after env.reset() and env.step({}).
    5. Optionally save the public observation and contract evidence.

Input
    Input/IEEE123_Base/IEEE123Master.dss (unchanged canonical feeder).
Output
    Output/04_observation_demo/ when SAVE_RESULTS=True.

Safety
    No external action channels, no external controller, no simulator patch.
    Native IEEE-123 regulators/capacitors retain their native authority.
"""

# =============================================================================
# SECTION 1 - IMPORTS: existing public OpenDSSSim API only
# =============================================================================
import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from opendsssim.environment import EpisodeSpec, OpenDSSSimulator
from opendsssim.problem import (
    CardinalityKind,
    CardinalityRequirement,
    ObservationSpec,
    ProblemSpec,
    RegistryKind,
    SelectionGroup,
    SemanticQuery,
)


# =============================================================================
# SECTION 2 - USER CONFIGURATION: settings worth changing first
# =============================================================================
HERE = Path(__file__).resolve().parent
CIRCUIT = HERE / "Input" / "IEEE123_Base" / "IEEE123Master.dss"
OUTPUT = HERE / "Output"
RUN_NAME = "04_observation_demo"  # Change to avoid replacing earlier results
STEPS = 3
SAVE_RESULTS = True
PRINT_ALL_BUS_VOLTAGES = False
RESET_SEED = 1


# =============================================================================
# SECTION 3 - CREATE PROBLEMSPEC: choose observations, not actions
# =============================================================================
# RegistryKind.STATE means an observed electrical/operating quantity.
# The SemanticQuery is resolved against *the feeder's actual semantic registry*.
# We do not hardcode 123 buses, phase order, native addresses, or array lengths.
# NONEMPTY means fail clearly if this feeder has no such registered channels.
nonempty = CardinalityRequirement(CardinalityKind.NONEMPTY)

problem = ProblemSpec.create(
    problem_id="tutorial-ieee123-observe",
    problem_version="1",
    observations=ObservationSpec(groups=(
        SelectionGroup(
            group_id="bus_voltages",
            selections=(SemanticQuery(
                RegistryKind.STATE,
                dss_class="Bus",
                quantity="bus_voltage_pu",
                cardinality=nonempty,
            ),),
            cardinality=nonempty,
        ),
        SelectionGroup(
            group_id="convergence",
            selections=(SemanticQuery(
                RegistryKind.STATE,
                quantity="solution_converged",
                cardinality=nonempty,
            ),),
            cardinality=nonempty,
        ),
    )),
    # No ActionSpec -> the Gym action is the empty dictionary {}.
    metadata={"course_example": 4, "purpose": "observations-only"},
)


# =============================================================================
# SECTION 4 - CONSTRUCT SIMULATOR: explicit public configuration
# =============================================================================
if not CIRCUIT.is_file():
    raise FileNotFoundError(CIRCUIT)
if STEPS < 1:
    raise ValueError("STEPS must be >= 1")

with TemporaryDirectory(prefix="opendsssim_e04_") as temporary:
    run = OUTPUT / RUN_NAME if SAVE_RESULTS else Path(temporary)
    if SAVE_RESULTS and run.exists():
        raise FileExistsError(f"Choose a new RUN_NAME, output exists: {run}")
    run.mkdir(parents=True, exist_ok=True)

    env = OpenDSSSimulator(
        network=CIRCUIT,
        backend="altdss",
        problem=problem,
        episode_spec=EpisodeSpec(
            start_time_utc="2026-01-01T00:00:00Z",
            dt_seconds=3600,
            max_steps=STEPS,
        ),
        history_level="H1",
        inventory_dir=run / "Inventory",
        semantic_registry_dir=run / "SemanticRegistry",
        preflight_dir=run / "Preflight",
    )

    try:
        # =====================================================================
        # SECTION 5 - INSPECT THE COMPILED CONTRACT BEFORE AND AFTER RESET
        # =====================================================================
        # Problem-aware environments compile action/observation spaces at
        # construction, using the feeder inventory and semantic registry.
        print("\nEXAMPLE 04 - IEEE-123 PROBLEMSPEC OBSERVATIONS")
        print("Authored ProblemSpec SHA256:", problem.problem_spec_sha256)
        print("Observation space:", env.observation_space)
        print("Action space:", env.action_space)
        print("Resolved observation groups and channel counts:")
        for group in env.resolved_problem.observations.groups:
            print("  ", group.group_id, "->", len(group.channels), "channels")
        print("Note: group_id organizes selection; it is NOT a Gym dict key.")

        observation, info = env.reset(seed=RESET_SEED)
        if not env.observation_space.contains(observation):
            raise RuntimeError("Reset observation violates the compiled Gym space")
        print("Preflight status:", env.preflight_status)
        print("Reset convergence:", info["solution"]["converged"])
        print("Top-level observation keys:", list(observation))

        # Canonical observation paths are based on native class/object/quantity:
        # observation['current']['Bus']['<bus>']['bus_voltage_pu'].
        buses = observation["current"]["Bus"]
        print("Observed bus objects:", len(buses))
        first_bus = next(iter(buses))
        print("First bus:", first_bus, "voltage components:",
              np.asarray(buses[first_bus]["bus_voltage_pu"]).tolist())
        if PRINT_ALL_BUS_VOLTAGES:
            for bus, quantities in buses.items():
                print("   ", bus, np.asarray(quantities["bus_voltage_pu"]).tolist())

        # =====================================================================
        # SECTION 6 - EXPLICIT GYM LOOP: observe; never issue physical actions
        # =====================================================================
        rows = []
        for step in range(1, STEPS + 1):
            action = {}  # Valid only because this ProblemSpec has no actions.
            observation, reward, terminated, truncated, info = env.step(action)
            if not env.observation_space.contains(observation):
                raise RuntimeError("Step observation violates compiled Gym space")

            # Bus voltage components follow registered native bus/node layouts.
            # These indices must NOT be silently described as A/B/C phases.
            values = [float(v)
                      for record in observation["current"]["Bus"].values()
                      for v in np.asarray(record["bus_voltage_pu"]).reshape(-1)
                      if float(v) > 1e-4]
            if not values:
                raise RuntimeError("No energized voltage components observed")
            row = {
                "step": step,
                "electrical_time_utc": info["time"]["electrical_sample_time_utc"],
                "converged": bool(info["solution"]["converged"]),
                "vmin_pu": min(values),
                "vmax_pu": max(values),
                "out_of_band_components": sum(not 0.95 <= v <= 1.05 for v in values),
            }
            rows.append(row)
            print(f"Step {step:02d} | AC={row['converged']} | "
                  f"Vmin={row['vmin_pu']:.4f} | Vmax={row['vmax_pu']:.4f} | "
                  f"outside 0.95-1.05={row['out_of_band_components']}")
            if terminated or truncated:
                break

        # =====================================================================
        # SECTION 7 - OPTIONAL OUTPUT: public objects and CSV summary
        # =====================================================================
        if SAVE_RESULTS:
            def save_json(name, value):
                (run / name).write_text(
                    json.dumps(value, indent=2, default=lambda x:
                               x.tolist() if hasattr(x, "tolist") else str(x)) + "\n",
                    encoding="utf-8",
                )

            with (run / "voltage_envelopes.csv").open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            save_json("authored_problem.json", problem.semantic_dict())
            save_json("resolved_problem.json", env.resolved_problem.semantic_dict())
            save_json("reset_observation.json", buses)
            save_json("history.json", env.history.records)
            print("Saved to:", run)
        else:
            print("SAVE_RESULTS=False: outputs are temporary; console only")
    finally:
        # =====================================================================
        # SECTION 8 - CLOSE THE AUTHORITATIVE SIMULATOR
        # =====================================================================
        env.close()
