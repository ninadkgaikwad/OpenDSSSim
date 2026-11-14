#!/usr/bin/env python
"""Standalone qualification validator for OpenDSSSim_A01_AltDSS_Foundation_Context_Snapshot_v01R1_20261005."""

from __future__ import annotations

import argparse
import json
import platform
import sys
import tempfile
from datetime import datetime, timezone
from importlib.metadata import version as package_version
from pathlib import Path


PATCH_ID = "OpenDSSSim_A01_AltDSS_Foundation_Context_Snapshot_v01R1_20261005"
EXPECTED_ALTDSS = "0.2.4"
EXPECTED_PREDECESSOR = "175411EEB2EFB0697D929E69DBD6EDCFE5524595A1E5D6F5426780EA9631E161"


def _add_src(repo_root: Path) -> None:
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    _add_src(repo_root)

    from opendsssim import A01_FOUNDATION_PATCH_ID
    from opendsssim import PRE_A01_SOURCE_MANIFEST_SHA256
    from opendsssim.environment.simulator import OpenDSSSimulator
    from opendsssim.persistence.manifest import write_runtime_manifest

    fixture = repo_root / "tests" / "fixtures" / "a01_minimal" / "Master.dss"
    if not fixture.exists():
        raise FileNotFoundError(f"Missing A01 DSS fixture: {fixture}")

    gates: dict[str, object] = {}

    gates["patch_id"] = A01_FOUNDATION_PATCH_ID == PATCH_ID
    gates["predecessor_identity"] = PRE_A01_SOURCE_MANIFEST_SHA256 == EXPECTED_PREDECESSOR
    gates["altdss_version"] = package_version("altdss") == EXPECTED_ALTDSS

    env_a = OpenDSSSimulator(fixture)
    env_b = OpenDSSSimulator(fixture)
    try:
        ctx_a = env_a.context_identity
        ctx_b = env_b.context_identity
        gates["context_isolation"] = ctx_a != ctx_b

        obs_a1, info_a1 = env_a.reset(seed=42)
        obs_b1, info_b1 = env_b.reset(seed=42)

        gates["solve_a_converged"] = bool(info_a1["solution"]["converged"])
        gates["solve_b_converged"] = bool(info_b1["solution"]["converged"])
        gates["gym_observation"] = env_a.observation_space.contains(obs_a1)
        gates["minimum_network_shape"] = (
            info_a1["solution"]["num_buses"] >= 2
            and info_a1["solution"]["num_nodes"] >= 4
            and info_a1["solution"]["num_circuit_elements"] >= 2
        )

        obs_step, reward, terminated, truncated, info_step = env_a.step({})
        gates["gym_step"] = (
            env_a.observation_space.contains(obs_step)
            and reward == 0.0
            and terminated is False
            and truncated is False
            and bool(info_step["solution"]["converged"])
        )

        ctx_before_reset = env_a.context_identity
        _, info_a2 = env_a.reset(seed=42)
        ctx_after_reset = env_a.context_identity

        p1 = info_a1["solution"]["total_power_kw"]
        q1 = info_a1["solution"]["total_power_kvar"]
        p2 = info_a2["solution"]["total_power_kw"]
        q2 = info_a2["solution"]["total_power_kvar"]

        gates["reset_same_context"] = ctx_before_reset == ctx_after_reset
        gates["reset_deterministic"] = abs(p1 - p2) <= 1e-9 and abs(q1 - q2) <= 1e-9

        with tempfile.TemporaryDirectory(prefix="opendsssim_a01_manifest_") as td:
            manifest_path = Path(td) / "runtime_manifest.json"
            manifest = write_runtime_manifest(
                manifest_path,
                repo_root=repo_root,
                engine_version=info_a2["solution"]["engine_version"],
                context_identity=env_a.context_identity,
            )
            manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            gates["runtime_manifest"] = (
                manifest_payload["patch_id"] == manifest.patch_id
                and len(manifest.current_source_identity_sha256) == 64
            )

        engine_version = info_a2["solution"]["engine_version"]

    finally:
        env_a.close()
        env_b.close()

    gates["close_lifecycle"] = True

    failed = [name for name, value in gates.items() if value is not True]

    report = {
        "patch_id": PATCH_ID,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "altdss": package_version("altdss"),
        "engine_version": engine_version,
        "repo_root": str(repo_root),
        "gates": gates,
        "status": "PASS" if not failed else "FAIL",
        "failed_gates": failed,
    }

    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else None
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = output_dir / f"OpenDSSSim_A01_StandaloneValidation_{stamp}.json"
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"REPORT={output}")

    print(json.dumps(report, indent=2, sort_keys=True))

    if failed:
        print("A01 STANDALONE VALIDATOR: FAIL")
        return 1

    print("A01 STANDALONE VALIDATOR: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
