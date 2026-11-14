#!/usr/bin/env python
"""Standalone qualification validator for OpenDSSSim_A02H1_Persistent_Circuit_Inventory_Native_Control_Discovery_v01R1_20261008."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

PATCH_ID = "OpenDSSSim_A02H1_Persistent_Circuit_Inventory_Native_Control_Discovery_v01R1_20261008"
EXPECTED_PREDECESSOR = "391A3AEC79882BFE2BCA7DF7DAFA2399AF42EE9A10A9FDD478727B5B84859983"


def _add_src(repo_root: Path) -> None:
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def _contains_forbidden_dynamic_keys(payload: object) -> bool:
    forbidden = {
        "solution_converged",
        "properties_json",
        "is_isolated",
        "context_identity",
    }
    if isinstance(payload, dict):
        if any(key in forbidden for key in payload):
            return True
        return any(_contains_forbidden_dynamic_keys(value) for value in payload.values())
    if isinstance(payload, list):
        return any(_contains_forbidden_dynamic_keys(value) for value in payload)
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    _add_src(repo_root)

    from opendsssim import A02_DISCOVERY_PATCH_ID
    from opendsssim import A02H1_PATCH_ID as INSTALLED_PATCH_ID
    from opendsssim.backends.altdss_backend import AltDSSBackend
    from opendsssim.discovery.native_controls import (
        NATIVE_CONTROL_CLASSES,
        discover_native_controls,
    )
    from opendsssim.environment.simulator import OpenDSSSimulator
    from opendsssim.network.loading import CircuitSource

    gates: dict[str, object] = {}
    gates["patch_id"] = INSTALLED_PATCH_ID == PATCH_ID
    gates["a02_predecessor_patch"] = (
        A02_DISCOVERY_PATCH_ID
        == "OpenDSSSim_A02_Generalized_Engine_Circuit_Capability_Discovery_v01R1_20261007"
    )
    gates["official_control_catalog"] = NATIVE_CONTROL_CLASSES == (
        "CapControl",
        "ESPVLControl",
        "ExpControl",
        "Fuse",
        "GenDispatcher",
        "InvControl",
        "Recloser",
        "RegControl",
        "Relay",
        "StorageController",
        "SwtControl",
        "UPFCControl",
    )

    control_fixture = (
        repo_root / "tests" / "fixtures" / "a02h1_control" / "Master.dss"
    )
    minimal_fixture = (
        repo_root / "tests" / "fixtures" / "a01_minimal" / "Master.dss"
    )

    with tempfile.TemporaryDirectory(prefix="opendsssim_a02h1_") as tmp:
        tmp_path = Path(tmp)

        # Source-tree fingerprint gate.
        source_case = tmp_path / "source_case"
        shutil.copytree(control_fixture.parent, source_case)
        source_a = CircuitSource.from_path(source_case / "Master.dss")
        gates["source_dependency_count"] = source_a.dependency_count == 3

        controls_path = source_case / "Controls.dss"
        controls_path.write_text(
            controls_path.read_text(encoding="utf-8") + "\n! changed\n",
            encoding="utf-8",
        )
        source_b = CircuitSource.from_path(source_case / "Master.dss")
        gates["nested_dependency_invalidation"] = (
            source_a.sha256 == source_b.sha256
            and source_a.source_tree_sha256 != source_b.source_tree_sha256
        )

        # Real native-control discovery gate.
        backend = AltDSSBackend()
        try:
            backend.load_circuit(CircuitSource.from_path(control_fixture))
            discovery = backend.discover_circuit()
            controls, relationships = discover_native_controls(discovery)
        finally:
            backend.close()

        control_names = {item.full_name.casefold() for item in controls}
        gates["real_control_objects"] = {
            "regcontrol.rc1",
            "capcontrol.cc1",
            "swtcontrol.sc1",
        }.issubset(control_names)

        relationship_triples = {
            (
                item.source_full_name.casefold(),
                item.role,
                (item.target_full_name or "").casefold(),
            )
            for item in relationships
        }
        gates["real_control_relationships"] = all(
            required in relationship_triples
            for required in (
                ("regcontrol.rc1", "CONTROLS", "transformer.regx"),
                ("capcontrol.cc1", "MONITORS", "line.feeder"),
                ("capcontrol.cc1", "CONTROLS", "capacitor.cap1"),
                ("swtcontrol.sc1", "SWITCHES", "line.feeder"),
            )
        )

        # Build-once/reuse gate.
        runtime_case = tmp_path / "runtime_case"
        runtime_case.mkdir()
        runtime_master = runtime_case / "Master.dss"
        shutil.copy2(minimal_fixture, runtime_master)
        cache = tmp_path / "inventory_cache"

        env_a = OpenDSSSimulator(runtime_master, inventory_dir=cache)
        try:
            gates["initial_cache_miss"] = env_a.inventory_status == "MISSING"
            env_a.reset(seed=11)
            gates["inventory_built"] = (
                env_a.inventory_status == "BUILT"
                and env_a.inventory_build_count == 1
                and env_a.inventory_path.exists()
            )

            inventory_a = env_a.circuit_inventory
            first_hash = inventory_a.semantic_sha256
            payload = json.loads(env_a.inventory_path.read_text(encoding="utf-8"))
            gates["inventory_static_only"] = not _contains_forbidden_dynamic_keys(payload)

            with patch.object(
                AltDSSBackend,
                "discover_circuit",
                side_effect=AssertionError("unexpected A02H1 rediscovery"),
            ):
                env_a.reset(seed=12)

            gates["same_env_no_rediscovery"] = (
                env_a.inventory_status == "REUSED"
                and env_a.inventory_build_count == 1
            )
        finally:
            env_a.close()

        env_b = OpenDSSSimulator(runtime_master, inventory_dir=cache)
        try:
            gates["new_env_cache_load"] = env_b.inventory_status == "LOADED"

            with patch.object(
                AltDSSBackend,
                "discover_circuit",
                side_effect=AssertionError("cached inventory rediscovery"),
            ):
                env_b.reset(seed=13)

            gates["new_env_no_rediscovery"] = (
                env_b.inventory_status == "REUSED"
                and env_b.inventory_build_count == 0
                and env_b.circuit_inventory.semantic_sha256 == first_hash
            )
        finally:
            env_b.close()

        dependency = runtime_case / "dependency.csv"
        dependency.write_text("1\n", encoding="utf-8")
        env_c = OpenDSSSimulator(runtime_master, inventory_dir=cache)
        try:
            gates["source_change_cache_miss"] = env_c.inventory_status == "MISSING"
        finally:
            env_c.close()

    failed = [name for name, value in gates.items() if value is not True]

    report = {
        "patch_id": PATCH_ID,
        "predecessor_source_manifest_sha256": EXPECTED_PREDECESSOR,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo_root),
        "gates": gates,
        "status": "PASS" if not failed else "FAIL",
        "failed_gates": failed,
    }

    if args.output_dir:
        output_dir = Path(args.output_dir).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = output_dir / f"OpenDSSSim_A02H1_StandaloneValidation_{stamp}.json"
        output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"REPORT={output}")

    print(json.dumps(report, indent=2, sort_keys=True))

    if failed:
        print("A02H1 STANDALONE VALIDATOR: FAIL")
        return 1

    print("A02H1 STANDALONE VALIDATOR: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
