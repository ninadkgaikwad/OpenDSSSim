from pathlib import Path
from unittest.mock import patch

from opendsssim.backends.altdss_backend import AltDSSBackend
from opendsssim.environment.simulator import OpenDSSSimulator
from opendsssim.semantics.schema import (
    Mutability,
    NativePropertyAddress,
    RuntimeCommandAddress,
    RuntimeReadoutAddress,
)


def _entries(bundle, ids):
    lookup = bundle.entry_by_id()
    return [lookup[item] for item in ids]


def test_a03_real_fixture_compiles_frozen_semantics(tmp_path: Path):
    fixture = Path(__file__).parents[1] / "fixtures" / "a03_semantic" / "Master.dss"
    env = OpenDSSSimulator(
        fixture,
        inventory_dir=tmp_path / "inventory",
        semantic_registry_dir=tmp_path / "semantic",
    )
    try:
        env.reset(seed=1)
        bundle = env.semantic_registry
        assert bundle is not None
        assert env.semantic_registry_status == "BUILT"
        assert env.semantic_registry_compile_count == 1

        assert bundle.capability_registry.has("observation.bus_voltage")
        assert bundle.capability_registry.has("control.pv_reactive_power")
        assert bundle.capability_registry.has("control.storage_active_power")
        assert bundle.capability_registry.has("control.storage_reactive_power")
        assert bundle.capability_registry.has("control.capacitor_switching")
        assert bundle.capability_registry.has("control.regulator_tap")
        assert bundle.capability_registry.has("control.branch_switching")
        assert bundle.capability_registry.has("service.topology")
        assert bundle.capability_registry.has("native_control.regulator")

        actions = _entries(bundle, bundle.action_registry.entry_ids)
        disturbances = _entries(bundle, bundle.disturbance_registry.entry_ids)
        parameters = _entries(bundle, bundle.parameter_registry.entry_ids)

        assert any(
            isinstance(item.address, NativePropertyAddress)
            and item.address.object_full_name.casefold() == "pvsystem.pv1"
            and item.address.property_name.casefold() == "kvar"
            and item.mutability is Mutability.STEP_CONTROLLABLE
            for item in actions
        )
        assert any(
            isinstance(item.address, RuntimeCommandAddress)
            and item.address.entity.casefold() == "transformer.regx"
            for item in actions
        )
        assert any(
            isinstance(item.address, RuntimeCommandAddress)
            and item.address.entity.casefold() == "line.feeder"
            and item.address.operation == "open_close"
            for item in actions
        )
        assert any(
            item.native_entity
            and item.native_entity.casefold() == "load.load1"
            and item.mutability is Mutability.STEP_EXOGENOUS
            for item in disturbances
        )
        assert any(
            item.native_entity
            and item.native_entity.casefold() == "pvsystem.pv1"
            and item.mutability is Mutability.STEP_EXOGENOUS
            for item in disturbances
        )

        # Conservative exclusions: writable configuration/control properties are
        # not automatically external actions.
        assert not any(
            isinstance(item.address, NativePropertyAddress)
            and item.address.object_full_name.casefold() == "line.feeder"
            and item.address.property_name.casefold() == "r1"
            for item in actions
        )
        assert not any(
            item.native_entity
            and item.native_entity.casefold() == "regcontrol.rc1"
            for item in actions
        )
        assert not any(
            item.native_entity
            and item.native_entity.casefold() == "generator.gen1"
            for item in actions
        )
        assert any(
            item.native_entity
            and item.native_entity.casefold() == "regcontrol.rc1"
            for item in parameters
        )

        states = _entries(bundle, bundle.state_registry.entry_ids)
        assert any(isinstance(item.address, RuntimeReadoutAddress) for item in states)
    finally:
        env.close()


def test_a03_registry_reuses_without_discovery_or_reclassification(tmp_path: Path):
    fixture = Path(__file__).parents[1] / "fixtures" / "a03_semantic" / "Master.dss"
    inventory_dir = tmp_path / "inventory"
    semantic_dir = tmp_path / "semantic"

    env_a = OpenDSSSimulator(
        fixture,
        inventory_dir=inventory_dir,
        semantic_registry_dir=semantic_dir,
    )
    try:
        env_a.reset(seed=2)
        first_hash = env_a.semantic_registry.semantic_sha256
        env_a.reset(seed=3)
        assert env_a.semantic_registry_status == "REUSED"
        assert env_a.semantic_registry_compile_count == 1
    finally:
        env_a.close()

    env_b = OpenDSSSimulator(
        fixture,
        inventory_dir=inventory_dir,
        semantic_registry_dir=semantic_dir,
    )
    try:
        assert env_b.inventory_status == "LOADED"
        assert env_b.semantic_registry_status == "LOADED"
        with patch.object(
            AltDSSBackend,
            "discover_circuit",
            side_effect=AssertionError("unexpected A02 discovery"),
        ), patch.object(
            AltDSSBackend,
            "read_object_properties",
            side_effect=AssertionError("unexpected A03 reclassification"),
        ):
            env_b.reset(seed=4)
        assert env_b.semantic_registry_status == "REUSED"
        assert env_b.semantic_registry_compile_count == 0
        assert env_b.semantic_registry.semantic_sha256 == first_hash
    finally:
        env_b.close()
