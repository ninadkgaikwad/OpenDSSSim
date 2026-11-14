from dataclasses import replace

import pytest

from opendsssim.problem import (
    A05DeferredError,
    ActionRestriction,
    ActionSpec,
    CapabilityRequirement,
    CardinalityKind,
    CardinalityRequirement,
    ControlAuthorityMode,
    ControlAuthoritySpec,
    ExactSemanticRef,
    ObservationSpec,
    ProblemResolutionError,
    ProblemSpec,
    RegistryKind,
    SelectionGroup,
    SemanticQuery,
    resolve_problem,
)

from ._helpers import first_id, make_inventory_and_bundle


def test_problem_spec_hash_is_deterministic_and_semantic():
    a = ProblemSpec.create("P", "1", metadata={"z": 2, "a": 1})
    b = ProblemSpec.create("P", "1", metadata={"a": 1, "z": 2})
    c = ProblemSpec.create("P", "2", metadata={"a": 1, "z": 2})
    assert a.problem_spec_sha256 == b.problem_spec_sha256
    assert a.problem_spec_sha256 != c.problem_spec_sha256


def test_exact_query_group_selection_preserves_authored_then_canonical_order():
    inventory, bundle = make_inventory_and_bundle()
    converged_id = first_id(bundle, RegistryKind.STATE, "solution_converged")
    spec = ProblemSpec(
        "P", "1",
        observations=ObservationSpec(
            groups=(
                SelectionGroup(
                    "mixed",
                    (
                        ExactSemanticRef(RegistryKind.STATE, converged_id),
                        SemanticQuery(
                            RegistryKind.STATE,
                            dss_class="Bus",
                            quantity="bus_voltage",
                            cardinality=CardinalityRequirement(CardinalityKind.EXACT, exact=2),
                        ),
                    ),
                    cardinality=CardinalityRequirement(CardinalityKind.EXACT, exact=3),
                ),
            )
        ),
    )
    resolved = resolve_problem(spec, bundle, inventory)
    channels = resolved.observations.groups[0].channels
    assert channels[0].quantity == "solution_converged"
    assert [item.object_name for item in channels[1:]] == ["b1", "b2"]


def test_query_cardinality_mismatch_fails_closed():
    inventory, bundle = make_inventory_and_bundle()
    spec = ProblemSpec(
        "P", "1",
        observations=ObservationSpec(
            groups=(
                SelectionGroup(
                    "buses",
                    (
                        SemanticQuery(
                            RegistryKind.STATE,
                            dss_class="Bus",
                            cardinality=CardinalityRequirement(CardinalityKind.EXACT, exact=3),
                        ),
                    ),
                ),
            )
        ),
    )
    with pytest.raises(ValueError, match="Cardinality failure"):
        resolve_problem(spec, bundle, inventory)


def test_duplicate_semantic_channel_fails_closed():
    inventory, bundle = make_inventory_and_bundle()
    semantic_id = first_id(bundle, RegistryKind.STATE, "solution_converged")
    ref = ExactSemanticRef(RegistryKind.STATE, semantic_id)
    spec = ProblemSpec(
        "P", "1",
        observations=ObservationSpec(groups=(SelectionGroup("g", (ref, ref)),)),
    )
    with pytest.raises(ProblemResolutionError, match="Duplicate semantic channel"):
        resolve_problem(spec, bundle, inventory)


def test_required_capability_and_resolved_hash_binding():
    inventory, bundle = make_inventory_and_bundle()
    spec = ProblemSpec(
        "P", "1",
        capability_requirements=(CapabilityRequirement("observation.bus_voltage"),),
    )
    resolved = resolve_problem(spec, bundle, inventory)
    assert resolved.satisfied_capabilities == ("observation.bus_voltage",)
    assert len(resolved.resolved_problem_sha256) == 64
    assert resolved.authored_problem_spec_sha256 == spec.problem_spec_sha256

    missing = replace(
        spec,
        capability_requirements=(CapabilityRequirement("capability.does.not.exist"),),
    )
    with pytest.raises(ProblemResolutionError, match="Required capability is absent"):
        resolve_problem(missing, bundle, inventory)


def test_forecast_groups_are_explicitly_deferred_to_a05():
    inventory, bundle = make_inventory_and_bundle()
    load_id = first_id(bundle, RegistryKind.DISTURBANCE, "load_active_power_driver")
    spec = ProblemSpec(
        "P", "1",
        observations=ObservationSpec(
            forecast_groups=(
                SelectionGroup(
                    "future_load",
                    (ExactSemanticRef(RegistryKind.DISTURBANCE, load_id),),
                ),
            )
        ),
    )
    with pytest.raises(A05DeferredError, match="A05-owned"):
        resolve_problem(spec, bundle, inventory)


def test_native_authority_rejects_external_actions():
    inventory, bundle = make_inventory_and_bundle()
    action_id = first_id(bundle, RegistryKind.ACTION, "pv_reactive_power_command")
    spec = ProblemSpec(
        "P", "1",
        actions=ActionSpec(
            groups=(SelectionGroup("pv", (ExactSemanticRef(RegistryKind.ACTION, action_id),)),)
        ),
    )
    with pytest.raises(ProblemResolutionError, match="NATIVE authority"):
        resolve_problem(spec, bundle, inventory)


def test_external_authority_defaults_exactly_to_selected_action_entities():
    inventory, bundle = make_inventory_and_bundle()
    action_id = first_id(bundle, RegistryKind.ACTION, "pv_reactive_power_command")
    spec = ProblemSpec(
        "P", "1",
        actions=ActionSpec(
            groups=(SelectionGroup("pv", (ExactSemanticRef(RegistryKind.ACTION, action_id),)),)
        ),
        control_authority=ControlAuthoritySpec(ControlAuthorityMode.EXTERNAL),
    )
    resolved = resolve_problem(spec, bundle, inventory)
    assert resolved.control_authority.external_entities == ("PVSystem.PV1",)


def test_problem_restriction_may_narrow_but_not_enlarge_intrinsic_bounds():
    inventory, bundle = make_inventory_and_bundle()
    action_id = first_id(bundle, RegistryKind.ACTION, "pv_reactive_power_command")
    base_group = SelectionGroup(
        "pv",
        (ExactSemanticRef(RegistryKind.ACTION, action_id),),
        action_restriction=ActionRestriction(low=-40.0, high=40.0),
    )
    spec = ProblemSpec(
        "P", "1",
        actions=ActionSpec((base_group,)),
        control_authority=ControlAuthoritySpec(ControlAuthorityMode.EXTERNAL),
    )
    channel = resolve_problem(spec, bundle, inventory).actions.groups[0].channels[0]
    assert (channel.static_low, channel.static_high) == (-40.0, 40.0)

    enlarged = replace(
        spec,
        actions=ActionSpec((replace(base_group, action_restriction=ActionRestriction(low=-61.0, high=40.0)),)),
    )
    with pytest.raises(ProblemResolutionError, match="enlarges intrinsic lower bound"):
        resolve_problem(enlarged, bundle, inventory)
