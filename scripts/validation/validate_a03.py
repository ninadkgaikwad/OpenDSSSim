#!/usr/bin/env python
"""Standalone qualification validator for OpenDSSSim A03 semantic registries."""

from __future__ import annotations

import argparse
from dataclasses import replace
from hashlib import sha256
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

PATCH_ID = "OpenDSSSim_A03_Persistent_Seven_Semantic_Registries_v01R4_20261010"
EXPECTED_PREDECESSOR = "B91845A265A8CA5E81AF317FEE0FBFF24B102256F672782F03E1DC797F23B00D"
EXPECTED_POLICY_SHA = "51062A587FF88E8B33A1CA2F6BA57B182D58AF8A83A16EE8D0CA0F7D072A98E3"

POLICY_DOCS = (
    "docs/development/architecture/OpenDSSSim_A03_Persistent_Seven_Semantic_Registries_Contract_v01_20261009.md",
    "docs/development/stages/A03_semantic_registries/README.md",
    "docs/development/stages/A03_semantic_registries/01_Scope_and_Boundaries.md",
    "docs/development/stages/A03_semantic_registries/02_Semantic_Address_and_Mutability_Model.md",
    "docs/development/stages/A03_semantic_registries/03_Seven_Registry_Contracts.md",
    "docs/development/stages/A03_semantic_registries/04_Class_by_Class_Semantic_Policy.md",
    "docs/development/stages/A03_semantic_registries/05_Persistence_Cache_Identity_and_Invalidation.md",
    "docs/development/stages/A03_semantic_registries/06_Runtime_Compilation_and_Reuse.md",
    "docs/development/stages/A03_semantic_registries/07_Capability_and_Controller_Compatibility.md",
    "docs/development/stages/A03_semantic_registries/08_Qualification_Plan_and_Evidence.md",
)


def _add_src(repo_root: Path) -> None:
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def _policy_sha(repo_root: Path) -> str:
    h = sha256()
    for rel in POLICY_DOCS:
        data = (repo_root / rel).read_bytes()
        h.update(rel.encode("utf-8"))
        h.update(b"\x00")
        h.update(data)
        h.update(b"\x00")
    return h.hexdigest().upper()


def _entries(bundle, ids):
    lookup = bundle.entry_by_id()
    return [lookup[item] for item in ids]


def _contains_forbidden_live_keys(payload: object) -> bool:
    forbidden = {
        "current_value",
        "realized_value",
        "requested_value",
        "applied_value",
        "properties_json",
        "context_identity",
    }
    if isinstance(payload, dict):
        if any(str(key) in forbidden for key in payload):
            return True
        return any(_contains_forbidden_live_keys(value) for value in payload.values())
    if isinstance(payload, list):
        return any(_contains_forbidden_live_keys(value) for value in payload)
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    _add_src(repo_root)

    from opendsssim import (
        A02H1_PATCH_ID,
        A03D1_DOCUMENTATION_PATCH_ID,
        PATCH_ID as INSTALLED_PATCH_ID,
        SEMANTIC_POLICY_SHA256,
    )
    from opendsssim.backends.altdss_backend import AltDSSBackend
    from opendsssim.environment.simulator import OpenDSSSimulator
    from opendsssim.persistence.semantic_registry import (
        validate_bundle_for_inventory,
    )
    from opendsssim.semantics.schema import (
        Mutability,
        NativePropertyAddress,
        RuntimeCommandAddress,
        RuntimeReadoutAddress,
    )

    fixture = repo_root / "tests" / "fixtures" / "a03_semantic" / "Master.dss"
    if not fixture.exists():
        raise FileNotFoundError(f"Missing A03 DSS fixture: {fixture}")

    gates: dict[str, object] = {}
    gates["patch_id"] = INSTALLED_PATCH_ID == PATCH_ID
    gates["a02h1_predecessor_patch"] = A02H1_PATCH_ID == (
        "OpenDSSSim_A02H1_Persistent_Circuit_Inventory_Native_Control_Discovery_v01R1_20261008"
    )
    gates["a03d1_predecessor_patch"] = A03D1_DOCUMENTATION_PATCH_ID == (
        "OpenDSSSim_A03D1_SemanticRegistries_DocumentationFreeze_v01_20261009"
    )
    gates["policy_constant"] = SEMANTIC_POLICY_SHA256 == EXPECTED_POLICY_SHA
    gates["policy_document_identity"] = _policy_sha(repo_root) == EXPECTED_POLICY_SHA

    with tempfile.TemporaryDirectory(prefix="opendsssim_a03_") as tmp:
        tmp_path = Path(tmp)
        inventory_dir = tmp_path / "inventory"
        semantic_dir = tmp_path / "semantic"

        env_a = OpenDSSSimulator(
            fixture,
            inventory_dir=inventory_dir,
            semantic_registry_dir=semantic_dir,
        )
        try:
            gates["initial_semantic_cache_waits_or_misses"] = (
                env_a.semantic_registry_status in {"WAITING_FOR_INVENTORY", "MISSING"}
            )
            obs, info = env_a.reset(seed=21)
            bundle = env_a.semantic_registry
            inventory = env_a.circuit_inventory
            gates["bundle_built"] = (
                bundle is not None
                and env_a.semantic_registry_status == "BUILT"
                and env_a.semantic_registry_compile_count == 1
                and env_a.semantic_registry_path is not None
                and env_a.semantic_registry_path.exists()
            )
            gates["gym_spaces_unchanged"] = (
                env_a.action_space.contains({})
                and env_a.observation_space.contains(obs)
                and set(obs) == {"converged"}
            )

            address_kinds = {item.address.kind for item in bundle.semantic_entries}
            gates["three_address_families"] = address_kinds == {
                "NATIVE_PROPERTY",
                "RUNTIME_READOUT",
                "RUNTIME_COMMAND",
            }
            mutabilities = {item.mutability for item in bundle.semantic_entries}
            gates["four_mutability_classes"] = mutabilities == set(Mutability)

            gates["seven_registries"] = all(
                value is not None
                for value in (
                    bundle.circuit_registry,
                    bundle.state_registry,
                    bundle.action_registry,
                    bundle.disturbance_registry,
                    bundle.constraint_registry,
                    bundle.parameter_registry,
                    bundle.capability_registry,
                )
            )

            actions = _entries(bundle, bundle.action_registry.entry_ids)
            disturbances = _entries(bundle, bundle.disturbance_registry.entry_ids)
            parameters = _entries(bundle, bundle.parameter_registry.entry_ids)
            constraints = _entries(bundle, bundle.constraint_registry.entry_ids)
            states = _entries(bundle, bundle.state_registry.entry_ids)

            action_entities = {
                (item.native_entity or "").casefold() for item in actions
            }
            gates["pv_action"] = "pvsystem.pv1" in action_entities
            gates["storage_actions"] = "storage.bess1" in action_entities
            gates["capacitor_action"] = "capacitor.cap1" in action_entities
            gates["transformer_tap_action"] = any(
                isinstance(item.address, RuntimeCommandAddress)
                and item.address.entity.casefold() == "transformer.regx"
                and item.address.operation == "set_tap"
                for item in actions
            )
            gates["switch_action"] = any(
                isinstance(item.address, RuntimeCommandAddress)
                and item.address.entity.casefold() == "line.feeder"
                and item.address.operation == "open_close"
                for item in actions
            )
            gates["generator_conservative_exclusion"] = (
                "generator.gen1" not in action_entities
            )
            gates["native_control_not_external_action"] = all(
                not entity.startswith((
                    "regcontrol.",
                    "capcontrol.",
                    "swtcontrol.",
                ))
                for entity in action_entities
            )
            gates["writable_line_property_not_action"] = not any(
                isinstance(item.address, NativePropertyAddress)
                and item.address.object_full_name.casefold() == "line.feeder"
                and item.address.property_name.casefold() == "r1"
                for item in actions
            )

            disturbance_entities = {
                (item.native_entity or "").casefold() for item in disturbances
            }
            gates["load_exogenous"] = "load.load1" in disturbance_entities
            gates["pv_exogenous"] = "pvsystem.pv1" in disturbance_entities
            gates["step_exogenous_distinct"] = all(
                item.mutability is Mutability.STEP_EXOGENOUS
                for item in disturbances
            )

            gates["runtime_readouts"] = any(
                isinstance(item.address, RuntimeReadoutAddress)
                for item in states
            )
            gates["native_controller_parameters"] = any(
                (item.native_entity or "").casefold() == "regcontrol.rc1"
                for item in parameters
            )
            gates["intrinsic_constraints"] = bool(constraints)
            gates["problem_voltage_band_absent"] = not any(
                "voltage_band" in item.quantity.casefold()
                for item in constraints
            )

            required_capabilities = {
                "observation.bus_voltage",
                "observation.element_current",
                "observation.element_power",
                "control.pv_reactive_power",
                "control.storage_active_power",
                "control.storage_reactive_power",
                "control.capacitor_switching",
                "control.regulator_tap",
                "control.branch_switching",
                "service.topology",
                "service.snapshot_solve",
                "native_control.regulator",
                "native_control.capacitor",
                "native_control.switch",
            }
            gates["capability_registry"] = required_capabilities.issubset(
                set(bundle.capability_registry.capability_ids)
            )

            payload = bundle.to_serialized_dict()
            gates["static_registry_only"] = not _contains_forbidden_live_keys(payload)
            gates["policy_bound_bundle"] = bundle.semantic_policy_sha256 == EXPECTED_POLICY_SHA

            gates["schema_invalidation"] = not validate_bundle_for_inventory(
                replace(bundle, registry_schema_version="future"), inventory
            )[0]
            gates["policy_invalidation"] = not validate_bundle_for_inventory(
                replace(bundle, semantic_policy_sha256="F" * 64), inventory
            )[0]

            first_hash = bundle.semantic_sha256
            with patch.object(
                AltDSSBackend,
                "discover_circuit",
                side_effect=AssertionError("unexpected A02 rediscovery"),
            ):
                env_a.reset(seed=22)
            gates["same_env_no_recompile"] = (
                env_a.semantic_registry_status == "REUSED"
                and env_a.semantic_registry_compile_count == 1
                and env_a.semantic_registry.semantic_sha256 == first_hash
            )
        finally:
            env_a.close()

        env_b = OpenDSSSimulator(
            fixture,
            inventory_dir=inventory_dir,
            semantic_registry_dir=semantic_dir,
        )
        try:
            gates["new_env_cache_load"] = (
                env_b.inventory_status == "LOADED"
                and env_b.semantic_registry_status == "LOADED"
            )
            with patch.object(
                AltDSSBackend,
                "discover_circuit",
                side_effect=AssertionError("unexpected A02 rediscovery"),
            ), patch.object(
                AltDSSBackend,
                "read_object_properties",
                side_effect=AssertionError("unexpected A03 reclassification"),
            ):
                env_b.reset(seed=23)
            gates["new_env_no_rediscovery_or_recompile"] = (
                env_b.semantic_registry_status == "REUSED"
                and env_b.semantic_registry_compile_count == 0
                and env_b.semantic_registry.semantic_sha256 == first_hash
            )
        finally:
            env_b.close()

        # Equivalent clean compilation into different cache roots is deterministic.
        env_c = OpenDSSSimulator(
            fixture,
            inventory_dir=tmp_path / "inventory_c",
            semantic_registry_dir=tmp_path / "semantic_c",
        )
        try:
            env_c.reset(seed=24)
            gates["deterministic_bundle_hash"] = (
                env_c.semantic_registry.semantic_sha256 == first_hash
            )
        finally:
            env_c.close()

        # Corrupted bundle is detected and rebuilt on reset.
        semantic_files = list(semantic_dir.glob("*.json"))
        assert len(semantic_files) == 1
        semantic_files[0].write_text("{corrupt", encoding="utf-8")
        env_d = OpenDSSSimulator(
            fixture,
            inventory_dir=inventory_dir,
            semantic_registry_dir=semantic_dir,
        )
        try:
            gates["corrupt_bundle_rejected"] = env_d.semantic_registry_status == "INVALID"
            env_d.reset(seed=25)
            gates["corrupt_bundle_rebuilt"] = (
                env_d.semantic_registry_status == "BUILT"
                and env_d.semantic_registry_compile_count == 1
            )
        finally:
            env_d.close()

        # Conservative whole-source-tree fingerprint causes a new A02H1/A03 identity.
        source_case = tmp_path / "source_case"
        shutil.copytree(fixture.parent, source_case)
        source_master = source_case / "Master.dss"
        first = OpenDSSSimulator(
            source_master,
            inventory_dir=tmp_path / "source_inventory",
            semantic_registry_dir=tmp_path / "source_semantic",
        )
        try:
            first.reset(seed=26)
        finally:
            first.close()
        (source_case / "dependency.csv").write_text("1\n", encoding="utf-8")
        second = OpenDSSSimulator(
            source_master,
            inventory_dir=tmp_path / "source_inventory",
            semantic_registry_dir=tmp_path / "source_semantic",
        )
        try:
            gates["source_change_invalidation"] = (
                second.inventory_status == "MISSING"
                and second.semantic_registry_status == "WAITING_FOR_INVENTORY"
            )
        finally:
            second.close()

    failed = [name for name, value in gates.items() if value is not True]
    report = {
        "patch_id": PATCH_ID,
        "predecessor_source_manifest_sha256": EXPECTED_PREDECESSOR,
        "semantic_policy_sha256": EXPECTED_POLICY_SHA,
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
        output = output_dir / f"OpenDSSSim_A03_StandaloneValidation_{stamp}.json"
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"REPORT={output}")

    print(json.dumps(report, indent=2, sort_keys=True))
    if failed:
        print("A03 STANDALONE VALIDATOR: FAIL")
        return 1
    print("A03 STANDALONE VALIDATOR: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
