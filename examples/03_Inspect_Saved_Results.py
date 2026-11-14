"""Example 03: inspect and plot saved hourly results. DOES NOT RUN AltDSS.

Requires a completed Example 02 output directory. It uses CSV/JSON only.
Edit RUN_NAME below to select which experiment to inspect.
"""

# =============================================================================
# 1. IMPORTS
# =============================================================================
import csv
from pathlib import Path


# =============================================================================
# 2. USER SETTINGS
# =============================================================================
HERE = Path(__file__).resolve().parent
RUN_NAME = "02_uncontrolled_24h"
RESULTS_CSV = HERE / "Output" / RUN_NAME / "hourly_results.csv"
SAVE_FIGURE = True


# =============================================================================
# 3. READ AN EXISTING RESULT — does not require the simulator
# =============================================================================
if not RESULTS_CSV.is_file():
    raise FileNotFoundError(
        f"No saved results: {RESULTS_CSV}\n"
        "Example 02 must be run natively before results can be inspected."
    )

with RESULTS_CSV.open(newline="", encoding="utf-8") as f:
    data = list(csv.DictReader(f))
if not data:
    raise ValueError("Results CSV is empty")

steps = [int(row["step"]) for row in data]
power = [float(row["total_power_kw"]) for row in data]
losses = [float(row["losses_kw"]) for row in data]

print("\nEXAMPLE 03 — SAVED RESULTS REVIEW (NO ALTDSS)")
print("Run:", RUN_NAME)
print("Rows:", len(data))
print("Time range:", data[0]["electrical_time_utc"], "to", data[-1]["electrical_time_utc"])
print("Power range kW:", round(min(power), 2), "to", round(max(power), 2))
print("Loss range kW:", round(min(losses), 2), "to", round(max(losses), 2))
print("Nonconverged steps:", [r["step"] for r in data if r["converged"].lower() != "true"])


# =============================================================================
# 4. OPTIONAL FIGURE (matplotlib is required only for this section)
# =============================================================================
if SAVE_FIGURE:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(steps, power, marker="o", label="Total power (kW)")
    ax.set_xlabel("Environment step")
    ax.set_ylabel("Total power (kW)")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    figure_path = RESULTS_CSV.parent / "power_timeseries.png"
    fig.savefig(figure_path, dpi=160)
    plt.close(fig)
    print("Saved figure:", figure_path)
