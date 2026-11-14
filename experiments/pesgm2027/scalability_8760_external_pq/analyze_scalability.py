from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import statistics


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--campaign-root", type=Path, required=True)
    args = p.parse_args()
    root = args.campaign_root.resolve()

    result = []
    for timing in sorted(root.glob("*/rep_*/timings.csv")):
        summary = json.loads(
            (timing.parent / "summary.json").read_text(
                encoding="utf-8"
            )
        )
        with timing.open(
            encoding="utf-8",
            newline="",
        ) as f:
            rows = list(csv.DictReader(f))

        engine = [
            float(x["engine_process_ms"])
            for x in rows
        ]
        step = [
            float(x["env_step_wall_ms"])
            for x in rows
        ]
        h3 = [
            float(x["debug_H3_serialize_gzip_ms"])
            for x in rows
        ]
        result.append(
            {
                "feeder": summary["feeder"],
                "num_buses": summary["circuit"]["num_buses"],
                "num_nodes": summary["circuit"]["num_nodes"],
                "num_elements": summary[
                    "circuit"
                ]["num_circuit_elements"],
                "num_loads": summary[
                    "circuit"
                ]["num_load_objects"],
                "steps": len(rows),
                "step_mean_ms": statistics.fmean(step),
                "step_median_ms": statistics.median(step),
                "engine_mean_ms": statistics.fmean(engine),
                "engine_median_ms": statistics.median(engine),
                "H3_serialize_mean_ms": statistics.fmean(h3),
                "H3_compressed_bytes": summary[
                    "debug_history"
                ]["compressed_bytes"],
            }
        )

    if not result:
        raise RuntimeError("NO_CAMPAIGN_TIMINGS_FOUND")

    out = root / "offline_scalability_analysis.json"
    out.write_text(
        json.dumps(
            {
                "schema": (
                    "OpenDSSSim.PESGM2027."
                    "Scalability8760.ExternalPQNativeH3."
                    "OfflineAnalysis.v02"
                ),
                "records": result,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"OFFLINE_ANALYSIS={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
