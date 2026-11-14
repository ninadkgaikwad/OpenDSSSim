#!/usr/bin/env python
"""Standalone qualification validator for OpenDSSSim_A02_Generalized_Engine_Circuit_Capability_Discovery_v01R1_20261007."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PATCH_ID = "OpenDSSSim_A02_Generalized_Engine_Circuit_Capability_Discovery_v01R1_20261007"
EXPECTED_PRE_A02_MANIFEST = "8D6A5D3548B90A515C38710B66ED6D814EE28E27C47E9D97FEAA680B7EE966A8"


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

    from opendsssim import A02_DISCOVERY_PATCH_ID
    from opendsssim.backends.base import CircuitNotLoadedError
    from opendsssim.environment.simulator import OpenDSSSimulator

    fixture = repo_root / "tests" / "fixtures" / "a01_minimal" / "Master.dss"
    if not fixture.exists():
        raise FileNotFoundError(f"Missing discovery fixture: {fixture}")

    gates: dict[str, object] = {}
    gates["patch_id"] = A02_DISCOVERY_PATCH_ID == PATCH_ID

    env_a = OpenDSSSimulator(fixture)
    env_b = OpenDSSSimulator(fixture)

    engine_version = ""
    semantic_sha256 = ""

    try:
        engine_a = env_a.discover_engine()
        engine_b = env_b.discover_engine()

        gates["engine_context_isolation"] = (
            engine_a.context_identity != engine_b.context_identity
        )
        gates["engine_features"] = all(
            feature in engine_a.feature_flags
            for feature in (
                "bus_inventory",
                "circuit_element_batch",
                "full_property_json",
                "independent_contexts",
                "node_inventory",
                "topology_summary",
            )
        )

        try:
            env_a.discover_circuit()
        except CircuitNotLoadedError:
            gates["requires_loaded_circuit"] = True
        else:
            gates["requires_loaded_circuit"] = False

        env_a.reset(seed=17)
        env_b.reset(seed=17)

        before_a = env_a.last_result.to_dict()
        first_a = env_a.discover_circuit()
        second_a = env_a.discover_circuit()
        first_b = env_b.discover_circuit()
        after_a = env_a.last_result.to_dict()

        gates["read_only"] = before_a == after_a
        gates["deterministic_repeat"] = (
            first_a.semantic_sha256 == second_a.semantic_sha256
            and first_a.to_dict() == second_a.to_dict()
        )
        gates["cross_context_semantic_parity"] = (
            first_a.semantic_sha256 == first_b.semantic_sha256
            and first_a.engine.context_identity != first_b.engine.context_identity
        )
        gates["json_serializable"] = bool(json.loads(first_a.to_json()))
        gates["circuit_shape"] = (
            first_a.num_buses >= 2
            and first_a.num_nodes >= 4
            and len(first_a.elements) == first_a.num_circuit_elements
        )

        object_names = {item.full_name.casefold() for item in first_a.objects}
        class_names = {item.dss_class.casefold() for item in first_a.classes}

        gates["native_objects"] = (
            "load.load1" in object_names
            and "line.feeder" in object_names
        )
        gates["native_classes"] = (
            "load" in class_names
            and "line" in class_names
        )
        gates["bus_inventory"] = (
            {bus.name.casefold() for bus in first_a.buses}
            >= {"source", "loadbus"}
        )
        gates["element_structure"] = all(
            element.num_phases >= 1
            and element.num_terminals >= 1
            and element.num_conductors >= 1
            for element in first_a.elements
        )

        load_obj = next(
            item for item in first_a.objects
            if item.full_name.casefold() == "load.load1"
        )
        load_properties = json.loads(load_obj.properties_json)
        gates["property_snapshot"] = (
            any(name.casefold() == "bus1" for name in load_obj.property_names)
            and any(name.casefold() == "kw" for name in load_obj.property_names)
            and isinstance(load_properties, dict)
        )

        _, _, _, _, step_info = env_a.step({})
        gates["post_discovery_solve"] = bool(step_info["solution"]["converged"])

        semantic_sha256 = first_a.semantic_sha256
        engine_version = first_a.engine.engine_version

    finally:
        env_a.close()
        env_b.close()

    failed = [name for name, value in gates.items() if value is not True]

    report = {
        "patch_id": PATCH_ID,
        "pre_a02_source_manifest_sha256": EXPECTED_PRE_A02_MANIFEST,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo_root),
        "engine_version": engine_version,
        "semantic_sha256": semantic_sha256,
        "gates": gates,
        "status": "PASS" if not failed else "FAIL",
        "failed_gates": failed,
    }

    if args.output_dir:
        output_dir = Path(args.output_dir).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = output_dir / f"OpenDSSSim_A02_StandaloneValidation_{stamp}.json"
        output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"REPORT={output}")

    print(json.dumps(report, indent=2, sort_keys=True))

    if failed:
        print("A02 STANDALONE VALIDATOR: FAIL")
        return 1

    print("A02 STANDALONE VALIDATOR: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
