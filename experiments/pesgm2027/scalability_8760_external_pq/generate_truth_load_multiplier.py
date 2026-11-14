from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import numpy as np

RAW_DAILY = np.array([
    0.78, 0.74, 0.72, 0.71, 0.73, 0.80,
    0.90, 1.02, 1.08, 1.10, 1.08, 1.05,
    1.03, 1.02, 1.00, 1.01, 1.05, 1.12,
    1.18, 1.20, 1.16, 1.08, 0.96, 0.86,
], dtype=float)
SEED = 8760
SIGMA = 0.02
CLIP_MIN = 0.65
CLIP_MAX = 1.30


def generate(path: Path) -> str:
    daily = RAW_DAILY / RAW_DAILY.mean()
    rng = np.random.default_rng(SEED)
    noise = rng.normal(0.0, SIGMA, 8760)
    base = np.tile(daily, 365)
    values = np.clip(base + noise, CLIP_MIN, CLIP_MAX)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "timestamp_utc", "day_index", "hour_of_day",
            "daily_base_multiplier_pu", "gaussian_noise_pu",
            "load_multiplier_pu",
        ])
        for i in range(8760):
            ts = start + timedelta(hours=i)
            w.writerow([
                ts.isoformat().replace("+00:00", "Z"),
                i // 24,
                i % 24,
                f"{base[i]:.12f}",
                f"{noise[i]:.12f}",
                f"{values[i]:.12f}",
            ])
    return sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--expect-sha256")
    args = p.parse_args()
    digest = generate(args.output)
    print(f"CSV_SHA256={digest}")
    if args.expect_sha256 and digest != args.expect_sha256.upper():
        raise SystemExit("PROFILE_SHA256_MISMATCH")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
