"""S06 general OpenDSSSim interface tests: no RBC/MPC/RL algorithm here.

Require genuinely native AltDSS resets/solves, no invented native readback.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from opendsssim.environment import OpenDSSSimulator, EpisodeSpec, ExogenousProfileSpec, LoadSeries
from opendsssim.problem import (ProblemSpec, ObservationSpec, ActionSpec, SelectionGroup,
    SemanticQuery, RegistryKind, ControlAuthoritySpec, ControlAuthorityMode)
from opendsssim.runtime import SemanticRuntimeAccess
from opendsssim.semantics.schema import NativePropertyAddress

FEEDERS = Path(__file__).resolve().parents[2] / "experiments" / "pesgm2027" / "feeders"
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "a03_semantic" / "Master.dss"


def _group(name, registry, quantity, **kwargs):
    return SelectionGroup(name, (SemanticQuery(registry, quantity=quantity, **kwargs),))


def _observation_problem(*quantities):
    return ProblemSpec.create('s06-array-observation', '1',
        observations=ObservationSpec(groups=(
            _group('converged', RegistryKind.STATE, 'solution_converged'),
            *(_group('observed'+str(i), RegistryKind.STATE, q) for i, q in enumerate(quantities)))))


def _service_problem(load='Load.Load1'):
    return ProblemSpec.create('s06-generic-load-service', '1',
        observations=ObservationSpec(groups=(
            _group('base_p', RegistryKind.STATE, 'load_available_active_demand_kw', native_entity=load),
            _group('base_q', RegistryKind.STATE, 'load_available_reactive_demand_kvar', native_entity=load),
            _group('fraction', RegistryKind.STATE, 'load_service_applied_fraction', native_entity=load),
            _group('converged', RegistryKind.STATE, 'solution_converged'))),
        actions=ActionSpec(groups=(
            _group('load_service', RegistryKind.ACTION, 'load_service_fraction', native_entity=load),)),
        control_authority=ControlAuthoritySpec(
            ControlAuthorityMode.EXTERNAL, external_entities=(load,)))


def _action(env, fraction):
    bindings = [b for b in env.runtime_binding.action_bindings
                if b.entry.quantity == 'load_service_fraction']
    assert len(bindings) == 1
    b = bindings[0]
    obj = {}
    cursor = obj
    for part in b.path[:-1]:
        cursor = cursor.setdefault(part, {})
    cursor[b.path[-1]] = np.array(fraction, dtype=np.float64)
    return obj


def _scalar(obs, quantity):
    for key, cls in obs['current'].items():
        for name, obj in cls.items():
            if quantity in obj:
                return float(obj[quantity])
    raise KeyError(quantity)


def _read(env, prop):
    return float(SemanticRuntimeAccess(env._plant.backend).read(
        NativePropertyAddress('Load.Load1', prop)))


@pytest.mark.parametrize('feeder,quantities', [
    ('ieee123_pesgm2027', ('capacitor_state', 'transformer_tap_position')),
    ('ieee123_p2_mf01_simple', ('branch_open_state',)),
    ('ieee123_p2_mf02_exotic', ('branch_open_state',)),
])
def test_native_shape_observations_compile_and_reset(tmp_path, feeder, quantities):
    env = OpenDSSSimulator(FEEDERS/feeder/'IEEE123Master.dss',
        problem=_observation_problem(*quantities),
        inventory_dir=tmp_path/'inv', semantic_registry_dir=tmp_path/'sem',
        preflight_dir=tmp_path/'pre')
    try:
        obs, info = env.reset()
        assert info['solution']['converged']
        assert env.observation_space.contains(obs)
        actual = [b for b in env.runtime_binding.observation_bindings if b.entry.quantity in quantities]
        assert actual
        assert {b.entry.quantity for b in actual} == set(quantities)
        assert all(b.entry.shape and b.layout.shape == b.entry.shape for b in actual)
        assert all(len(b.entry.shape) == 1 and b.entry.shape[0] > 0 for b in actual)
    finally:
        env.close()


def test_load_service_native_demand_scaling_and_no_compounding(tmp_path):
    env = OpenDSSSimulator(FIXTURE, problem=_service_problem(),
        episode_spec=EpisodeSpec(max_steps=3),
        inventory_dir=tmp_path/'inv', semantic_registry_dir=tmp_path/'sem',
        preflight_dir=tmp_path/'pre')
    try:
        obs, info = env.reset()
        assert info['solution']['converged']
        assert _scalar(obs, 'load_service_applied_fraction') == pytest.approx(1.0)
        assert _scalar(obs, 'load_available_active_demand_kw') == pytest.approx(250.0)
        assert _read(env, 'kW') == pytest.approx(250.0)
        for frac, expected in ((0.5, 125.0), (0.5, 125.0), (1.0, 250.0)):
            obs, reward, terminated, truncated, info = env.step(_action(env, frac))
            assert info['solution']['converged']
            assert info['action_audit'][0]['status'] == 'ADMISSIBLE_APPLIED'
            assert info['action_audit'][0]['realized_value'] == pytest.approx(frac)
            assert _scalar(obs, 'load_service_applied_fraction') == pytest.approx(frac)
            assert _scalar(obs, 'load_available_active_demand_kw') == pytest.approx(250.0)
            assert _read(env, 'kW') == pytest.approx(expected)
            assert _read(env, 'kvar') == pytest.approx(80.0 * frac)
        obs, info = env.reset()
        assert info['solution']['converged']
        assert _read(env, 'kW') == pytest.approx(250.0)
        assert _scalar(obs, 'load_service_applied_fraction') == pytest.approx(1.0)
    finally:
        env.close()


def test_service_exogenous_truth_stays_separate_and_replays_each_step(tmp_path):
    exogenous = ExogenousProfileSpec('s06-explicit-load-demand', loads=(
        LoadSeries(('Load.Load1',), 'absolute_pq', ((30.0, 10.0), (40.0, 12.0))),))
    env = OpenDSSSimulator(FIXTURE, problem=_service_problem(),
        exogenous=exogenous, episode_spec=EpisodeSpec(max_steps=2),
        inventory_dir=tmp_path/'inv', semantic_registry_dir=tmp_path/'sem',
        preflight_dir=tmp_path/'pre')
    try:
        obs, info = env.reset()
        assert _scalar(obs, 'load_available_active_demand_kw') == pytest.approx(30.0)
        assert _scalar(obs, 'load_service_applied_fraction') == pytest.approx(1.0)
        obs, _, _, _, info = env.step(_action(env, 0.5))
        assert info['solution']['converged']
        assert _read(env, 'kW') == pytest.approx(15.0)
        assert _read(env, 'kvar') == pytest.approx(5.0)
        assert _scalar(obs, 'load_available_active_demand_kw') == pytest.approx(30.0)
        obs, _, _, truncated, info = env.step(_action(env, 0.25))
        assert truncated and info['solution']['converged']
        assert _read(env, 'kW') == pytest.approx(10.0)
        assert _read(env, 'kvar') == pytest.approx(3.0)
        assert _scalar(obs, 'load_available_active_demand_kw') == pytest.approx(40.0)
        assert _scalar(obs, 'load_available_reactive_demand_kvar') == pytest.approx(12.0)
        assert _scalar(obs, 'load_service_applied_fraction') == pytest.approx(0.25)
        assert tuple(env._exogenous_last_audit['bindings'][0]['specified_kw_kvar']) == (40.0, 12.0)
    finally:
        env.close()


def test_action_domain_and_context_authority(tmp_path):
    env = OpenDSSSimulator(FIXTURE, problem=_service_problem(),
        inventory_dir=tmp_path/'inv', semantic_registry_dir=tmp_path/'sem',
        preflight_dir=tmp_path/'pre')
    try:
        obs, info = env.reset()
        ctx = env.controller_context()
        assert any(d.native_entity.casefold() == 'load.load1' and d.commandability == 'EXTERNAL_READY'
                   for d in ctx.devices)
        binding = next(b for b in env.runtime_binding.action_bindings
                       if b.entry.quantity == 'load_service_fraction')
        assert (binding.layout.low, binding.layout.high) == (0.0, 1.0)
        with pytest.raises(ValueError, match='Gym action space'):
            env.step(_action(env, 1.1))
        # Invalid requested action cannot mutate the native load.
        assert _read(env, 'kW') == pytest.approx(250.0)
    finally:
        env.close()
