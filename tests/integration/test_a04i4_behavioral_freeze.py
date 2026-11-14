from __future__ import annotations

from pathlib import Path
import numpy as np
import pytest

from opendsssim.environment.simulator import OpenDSSSimulator
from opendsssim.problem import (
    ActionSpec, ControlAuthorityMode, ControlAuthoritySpec, DeviceRef, FaultSpec,
    ObservationSpec, ProblemSpec, RegistryKind, SelectionGroup, SemanticQuery,
    compile_gym_spaces, resolve_problem,
)
from opendsssim.runtime import HistoryLevel, SemanticRuntimeAccess, build_runtime_binding
from opendsssim.runtime.binding import RuntimeBindingError
from opendsssim.semantics.schema import NativePropertyAddress

FIXTURE = Path(__file__).parents[1] / 'fixtures' / 'a03_semantic' / 'Master.dss'


def _problem(mode=ControlAuthorityMode.EXTERNAL, *, fault=False):
    return ProblemSpec.create(
        'a04i4-end-to-end', f'{mode.value}-fault{int(fault)}',
        observations=ObservationSpec(groups=(SelectionGroup('obs', (
            SemanticQuery(RegistryKind.STATE, dss_class='Solution', object_name='__service__', quantity='solution_converged'),
        )),)),
        actions=ActionSpec(groups=(SelectionGroup('tap', (
            SemanticQuery(RegistryKind.ACTION, native_entity='Transformer.RegX', quantity='transformer_tap_command'),
        )),)),
        control_authority=ControlAuthoritySpec(
            mode, external_entities=('Transformer.RegX',),
            native_entities=('Capacitor.Cap1',) if mode == ControlAuthorityMode.HYBRID else (),
        ),
        faults=(FaultSpec('disabled_transformer', (DeviceRef('Transformer.RegX'),)),) if fault else (),
    )


def _action(env, value):
    binding=next(b for b in env.runtime_binding.action_bindings if b.entry.quantity=='transformer_tap_command')
    root={}; node=root
    for part in binding.path[:-1]: node=node.setdefault(part,{})
    node[binding.path[-1]]=np.array(value,dtype=np.float64)
    assert env.action_space.contains(root)
    return root


@pytest.mark.parametrize('authority',[ControlAuthorityMode.EXTERNAL,ControlAuthorityMode.HYBRID])
def test_a04i4_multiple_steps_resets_authority_and_history(tmp_path,authority):
    env=OpenDSSSimulator(FIXTURE,problem=_problem(authority), inventory_dir=tmp_path/'inv',
        semantic_registry_dir=tmp_path/'sem',preflight_dir=tmp_path/'pre',history_level=HistoryLevel.H3)
    try:
        identity=env.context_identity
        obs,info=env.reset()
        assert env.observation_space.contains(obs)
        access=SemanticRuntimeAccess(env._plant.backend)
        assert bool(access.read(NativePropertyAddress('RegControl.RC1','Enabled'))) is False
        if authority == ControlAuthorityMode.HYBRID:
            assert bool(access.read(NativePropertyAddress('CapControl.CC1','Enabled'))) is True
        for i,value in enumerate((1.025,1.0,1.025),start=1):
            obs,reward,terminated,truncated,info=env.step(_action(env,value))
            assert env.context_identity==identity
            assert env.observation_space.contains(obs)
            assert reward==0.0 and not terminated and not truncated
            assert info['action_audit'][0]['status']=='ADMISSIBLE_APPLIED'
            assert info['action_audit'][0]['realized_value'][1]==pytest.approx(value)
            assert len(env.history)==i+1
            assert env.history[i]['full_state']
        obs,_=env.reset()
        assert env.context_identity==identity
        assert env.observation_space.contains(obs)
        assert len(env.history)==1
        assert bool(access.read(NativePropertyAddress('RegControl.RC1','Enabled'))) is False
    finally: env.close()


def test_a04i4_cache_reuse_is_bounded_to_source_and_problem(tmp_path):
    config=dict(inventory_dir=tmp_path/'inv',semantic_registry_dir=tmp_path/'sem',preflight_dir=tmp_path/'pre')
    statuses=[]; hashes=[]
    for run in range(2):
        env=OpenDSSSimulator(FIXTURE,problem=_problem(),**config)
        try:
            statuses.append(env.preflight_status)
            hashes.append(env.runtime_binding.runtime_binding_sha256)
            obs,_=env.reset()
            assert env.observation_space.contains(obs)
            _,_,_,_,info=env.step(_action(env,1.025))
            assert info['action_audit'][0]['status']=='ADMISSIBLE_APPLIED'
        finally: env.close()
    assert statuses==['BUILT','REUSED']
    assert hashes[0]==hashes[1]


def test_a04i4_external_switches_relationship_requires_native_suppression(tmp_path):
    problem=ProblemSpec.create('a04i4-switch-successor','1',
        observations=ObservationSpec(groups=(SelectionGroup('obs',(
            SemanticQuery(RegistryKind.STATE,quantity='solution_converged'),)),)),
        actions=ActionSpec(groups=(SelectionGroup('switch',(
            SemanticQuery(RegistryKind.ACTION,native_entity='Line.Feeder',quantity='branch_switch_command'),)),)),
        control_authority=ControlAuthoritySpec(ControlAuthorityMode.EXTERNAL,external_entities=('Line.Feeder',)))
    env=OpenDSSSimulator(FIXTURE,problem=problem,inventory_dir=tmp_path/'inv',
        semantic_registry_dir=tmp_path/'sem',preflight_dir=tmp_path/'pre')
    try:
        assert tuple(name.casefold() for name in env.runtime_binding.disabled_native_controls)==('swtcontrol.sc1',)
        env.reset()
        access=SemanticRuntimeAccess(env._plant.backend)
        assert access.read(NativePropertyAddress('SwtControl.SC1','Enabled')) is False
        assert access.read(NativePropertyAddress('RegControl.RC1','Enabled')) is True
        assert access.read(NativePropertyAddress('CapControl.CC1','Enabled')) is True
    finally: env.close()
