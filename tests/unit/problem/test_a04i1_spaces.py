import numpy as np

from gymnasium import spaces

from opendsssim.problem import (
    ActionSpec,
    ControlAuthorityMode,
    ControlAuthoritySpec,
    ExactSemanticRef,
    ObservationSpec,
    ProblemSpec,
    RegistryKind,
    SelectionGroup,
    SemanticQuery,
    compile_gym_spaces,
    resolve_problem,
)

from ._helpers import first_id, make_inventory_and_bundle


def _resolved_problem():
    inventory, bundle = make_inventory_and_bundle()
    pv_id = first_id(bundle, RegistryKind.ACTION, "pv_reactive_power_command")
    storage_id = first_id(bundle, RegistryKind.ACTION, "storage_active_power_command")
    tap_id = first_id(bundle, RegistryKind.ACTION, "transformer_tap_command")
    switch_id = first_id(bundle, RegistryKind.ACTION, "branch_switch_command")
    spec = ProblemSpec(
        "P", "1",
        observations=ObservationSpec(
            groups=(
                SelectionGroup(
                    "bus_voltage",
                    (SemanticQuery(RegistryKind.STATE, dss_class="Bus", quantity="bus_voltage"),),
                ),
            )
        ),
        actions=ActionSpec(
            groups=(
                SelectionGroup(
                    "controls",
                    tuple(
                        ExactSemanticRef(RegistryKind.ACTION, item)
                        for item in (pv_id, storage_id, tap_id, switch_id)
                    ),
                ),
            )
        ),
        control_authority=ControlAuthoritySpec(ControlAuthorityMode.EXTERNAL),
    )
    return resolve_problem(spec, bundle, inventory)


def test_static_action_bounds_are_resolved_from_a03_parameters():
    resolved = _resolved_problem()
    by_quantity = {
        channel.quantity: channel
        for group in resolved.actions.groups
        for channel in group.channels
    }
    assert (by_quantity["pv_reactive_power_command"].static_low,
            by_quantity["pv_reactive_power_command"].static_high) == (-60.0, 50.0)
    assert (by_quantity["storage_active_power_command"].static_low,
            by_quantity["storage_active_power_command"].static_high) == (-100.0, 100.0)
    assert (by_quantity["transformer_tap_command"].static_low,
            by_quantity["transformer_tap_command"].static_high) == (0.9, 1.1)
    assert by_quantity["branch_switch_command"].allowed_values == ("OPEN", "CLOSED")


def test_complex_observation_encoding_is_lossless_real_imag_final_axis():
    compiled = compile_gym_spaces(_resolved_problem())
    first = compiled.observation_layout[0]
    assert first.component_order == ("real", "imag")
    assert first.shape == (3, 2)
    assert first.dtype == "float64"
    assert first.path[:2] == ("current", "Bus")

    current = compiled.observation_space["current"]
    leaf = current["Bus"][first.path[2]]["bus_voltage"]
    assert isinstance(leaf, spaces.Box)
    assert leaf.shape == (3, 2)
    assert leaf.dtype == np.dtype(np.float64)


def test_action_spaces_and_layout_are_semantic_and_reversible():
    compiled = compile_gym_spaces(_resolved_problem())
    by_quantity = {item.path[-1]: item for item in compiled.action_layout}
    assert by_quantity["pv_reactive_power_command"].space_type == "Box"
    assert by_quantity["branch_switch_command"].space_type == "Discrete"
    assert by_quantity["branch_switch_command"].domain_values == ("OPEN", "CLOSED")
    assert by_quantity["transformer_tap_command"].low == 0.9
    assert by_quantity["transformer_tap_command"].high == 1.1
    assert len(compiled.action_space_sha256) == 64
    assert len(compiled.observation_space_sha256) == 64
    assert len(compiled.gym_space_contract_sha256) == 64


def test_space_hashes_are_deterministic():
    a = compile_gym_spaces(_resolved_problem())
    b = compile_gym_spaces(_resolved_problem())
    assert a.observation_space_sha256 == b.observation_space_sha256
    assert a.action_space_sha256 == b.action_space_sha256
    assert a.gym_space_contract_sha256 == b.gym_space_contract_sha256


def test_problem_none_preserves_legacy_empty_action_contract():
    inventory, bundle = make_inventory_and_bundle()
    assert resolve_problem(None, bundle, inventory) is None
    compiled = compile_gym_spaces(None)
    assert compiled.problem_mode == "NONE"
    assert set(compiled.observation_space.spaces) == {"converged"}
    assert compiled.action_space.contains({})
    assert compiled.observation_space.contains({"converged": 1})
