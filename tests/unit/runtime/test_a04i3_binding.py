from __future__ import annotations

from opendsssim.backends.base import DistributionBackend
from opendsssim.problem import (
    ActionSpec, ControlAuthorityMode, ControlAuthoritySpec, ObservationSpec, ProblemSpec,
    RegistryKind, SelectionGroup, SemanticQuery, compile_gym_spaces, resolve_problem,
)
from opendsssim.runtime.binding import build_runtime_binding
from tests.unit.problem._helpers import make_inventory_and_bundle


class FakeBackend(DistributionBackend):
    context_identity = 1
    engine_version = "test-engine"
    loaded_source = None
    is_closed = False
    def load_circuit(self, source): raise NotImplementedError
    def reset_circuit(self): raise NotImplementedError
    def solve_snapshot(self): raise NotImplementedError
    def discover_engine(self): raise NotImplementedError
    def discover_circuit(self): raise NotImplementedError
    def read_object_properties(self, object_full_name, property_names): return {}
    def write_object_property(self, object_full_name, property_name, value): return value
    def read_runtime_channel(self, service, entity, channel): return True
    def apply_runtime_command(self, service, entity, operation, value): return value
    def close(self): pass


def _problem():
    return ProblemSpec.create(
        "binding", "1",
        observations=ObservationSpec(groups=(SelectionGroup("obs", (SemanticQuery(RegistryKind.STATE, quantity="solution_converged"),)),)),
        actions=ActionSpec(groups=(SelectionGroup("act", (SemanticQuery(RegistryKind.ACTION, native_entity="PVSystem.PV1", quantity="pv_reactive_power_command"),)),)),
        control_authority=ControlAuthoritySpec(ControlAuthorityMode.EXTERNAL, external_entities=("PVSystem.PV1",)),
    )


def test_a04i3_runtime_binding_hash_is_deterministic_and_address_based():
    inventory, bundle = make_inventory_and_bundle()
    resolved = resolve_problem(_problem(), bundle, inventory)
    spaces = compile_gym_spaces(resolved)
    first = build_runtime_binding(resolved, spaces, bundle, inventory, FakeBackend())
    second = build_runtime_binding(resolved, spaces, bundle, inventory, FakeBackend())
    assert first.runtime_binding_sha256 == second.runtime_binding_sha256
    assert first.action_bindings[0].entry.address.kind == "NATIVE_PROPERTY"
    assert first.disabled_native_controls == ()
    assert first.fault_targets == ()
