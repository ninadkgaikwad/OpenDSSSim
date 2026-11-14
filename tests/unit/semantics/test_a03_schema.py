from dataclasses import replace

from opendsssim.semantics.schema import (
    ActionRegistry,
    CapabilityRecord,
    CapabilityRegistry,
    CircuitRegistry,
    ConstraintRegistry,
    DisturbanceRegistry,
    Mutability,
    NativePropertyAddress,
    ParameterRegistry,
    RuntimeCommandAddress,
    RuntimeReadoutAddress,
    SEMANTIC_POLICY_VERSION,
    SEMANTIC_REGISTRY_SCHEMA_VERSION,
    SemanticEntry,
    SemanticRegistryBundle,
    StateRegistry,
    deterministic_semantic_id,
)


def _entry(address, quantity, mutability):
    return SemanticEntry(
        semantic_id=deterministic_semantic_id(address, quantity),
        address=address,
        native_entity=None,
        quantity=quantity,
        unit=None,
        dtype="float",
        shape=(),
        selectors=(),
        mutability=mutability,
        static_metadata=(),
        capability_tags=(),
    )


def test_all_address_families_round_trip():
    addresses = (
        NativePropertyAddress("PVSystem.PV1", "kvar"),
        RuntimeReadoutAddress("Bus", "bus1", "pu_voltage"),
        RuntimeCommandAddress("CircuitElement", "Line.SW1", "open_close"),
    )
    entries = tuple(
        _entry(address, f"q{i}", Mutability.READ_ONLY)
        for i, address in enumerate(addresses)
    )
    bundle = SemanticRegistryBundle(
        registry_schema_version=SEMANTIC_REGISTRY_SCHEMA_VERSION,
        semantic_policy_version=SEMANTIC_POLICY_VERSION,
        semantic_policy_sha256="A" * 64,
        source_inventory_semantic_sha256="B" * 64,
        source_tree_sha256="C" * 64,
        backend="altdss",
        altdss_version="0.2.4",
        engine_version="engine",
        semantic_entries=entries,
        circuit_registry=CircuitRegistry("c", (), (), (), (), ()),
        state_registry=StateRegistry((entries[0].semantic_id,)),
        action_registry=ActionRegistry((entries[1].semantic_id,)),
        disturbance_registry=DisturbanceRegistry((entries[2].semantic_id,)),
        constraint_registry=ConstraintRegistry(()),
        parameter_registry=ParameterRegistry(()),
        capability_registry=CapabilityRegistry(
            (CapabilityRecord("service.test", (), ()),)
        ),
    )
    rebuilt = SemanticRegistryBundle.from_dict(bundle.to_serialized_dict())
    assert rebuilt == bundle
    assert rebuilt.semantic_sha256 == bundle.semantic_sha256


def test_mutability_has_exact_frozen_members():
    assert {item.value for item in Mutability} == {
        "READ_ONLY",
        "INIT_ONLY",
        "STEP_CONTROLLABLE",
        "STEP_EXOGENOUS",
    }


def test_semantic_id_is_deterministic_and_address_sensitive():
    a = NativePropertyAddress("Load.L1", "kW")
    b = NativePropertyAddress("Load.L1", "kvar")
    assert deterministic_semantic_id(a, "load") == deterministic_semantic_id(a, "load")
    assert deterministic_semantic_id(a, "load") != deterministic_semantic_id(b, "load")


def test_bundle_hash_changes_when_policy_identity_changes():
    entry = _entry(
        RuntimeReadoutAddress("Solution", None, "converged"),
        "solution_converged",
        Mutability.READ_ONLY,
    )
    base = SemanticRegistryBundle(
        registry_schema_version=SEMANTIC_REGISTRY_SCHEMA_VERSION,
        semantic_policy_version=SEMANTIC_POLICY_VERSION,
        semantic_policy_sha256="A" * 64,
        source_inventory_semantic_sha256="B" * 64,
        source_tree_sha256="C" * 64,
        backend="altdss",
        altdss_version="0.2.4",
        engine_version="engine",
        semantic_entries=(entry,),
        circuit_registry=CircuitRegistry("c", (), (), (), (), ()),
        state_registry=StateRegistry((entry.semantic_id,)),
        action_registry=ActionRegistry(()),
        disturbance_registry=DisturbanceRegistry(()),
        constraint_registry=ConstraintRegistry(()),
        parameter_registry=ParameterRegistry(()),
        capability_registry=CapabilityRegistry(()),
    )
    changed = replace(base, semantic_policy_sha256="D" * 64)
    assert changed.semantic_sha256 != base.semantic_sha256
