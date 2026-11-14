"""Real IEEE123 A05I6 controlled-client integration; no P1/P2 algorithms claimed."""
from pathlib import Path
import csv
import numpy as np
import pytest

from opendsssim.environment import (
    OpenDSSSimulator, ReplaySource, ReplayBinding, ReplaySpec,
    ForecastNoiseSpec, GaussianScale, ControllerInformationError,
    ControllerContextUnavailable, ForecastCoverageError,
)
from opendsssim.problem import (ProblemSpec, ObservationSpec, ActionSpec,
    ControlAuthoritySpec, ControlAuthorityMode, SelectionGroup, SemanticQuery, RegistryKind)
from opendsssim.semantics.schema import NativePropertyAddress
from opendsssim.runtime.access import SemanticRuntimeAccess

FEEDERS=Path(__file__).resolve().parents[2]/'experiments'/'pesgm2027'/'feeders'


def problem(with_pv_action):
    args={}
    if with_pv_action:
        args['actions']=ActionSpec(groups=(SelectionGroup('pv',(
            SemanticQuery(RegistryKind.ACTION,native_entity='PVSystem.PVD47',
                          quantity='pv_reactive_power_command'),)),))
        args['control_authority']=ControlAuthoritySpec(
            ControlAuthorityMode.EXTERNAL,external_entities=('PVSystem.PVD47',))
    return ProblemSpec.create('a05i6-client','1', observations=ObservationSpec(
        groups=(SelectionGroup('measure',(
            SemanticQuery(RegistryKind.STATE,quantity='solution_converged'),)),)), **args)


def action_for(env, q):
    b=next(x for x in env.runtime_binding.action_bindings if x.entry.quantity=='pv_reactive_power_command')
    result={}; current=result
    for key in b.path[:-1]:current=current.setdefault(key,{})
    current[b.path[-1]]=np.array(q,dtype=np.float64)
    assert env.action_space.contains(result)
    return result


def replay(tmp_path,with_pv,mode):
    l=tmp_path/'load.csv'
    with l.open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f);w.writerow(('time','p','q'))
        w.writerows((('2026-01-01T00:00:00Z',32,11),('2026-01-01T01:00:00Z',25,5)))
    sources=[ReplaySource('L','time','UTC',l)]
    bindings=[ReplayBinding('L','load',('Load.S1a','Load.S2b'),'absolute_pq',
                           ('p','q'),('kW','kvar'))]
    if with_pv:
        p=tmp_path/'pv.csv'
        with p.open('w',encoding='utf-8',newline='') as f:
            w=csv.writer(f);w.writerow(('time','g'))
            w.writerows((('2026-01-01T00:00:00Z',.8),('2026-01-01T01:00:00Z',.7)))
        sources.append(ReplaySource('P','time','UTC',p))
        bindings.append(ReplayBinding('P','pv',('PVSystem.PVD47','PVSystem.PVD76'),
                                      'irradiance',('g',),('kW/m2',)))
    return ReplaySpec(tuple(sources),tuple(bindings),mode=mode,max_steps=3)


@pytest.mark.parametrize('feeder',['ieee123_base','ieee123_pesgm2027'])
@pytest.mark.parametrize('mode',['strict','tile'])
def test_controller_context_snapshot_is_authorized_and_no_solve(tmp_path,feeder,mode):
    working=feeder=='ieee123_pesgm2027'
    scales=[
        GaussianScale('load.kw','Load.S1a',sigma=2.0),
        GaussianScale('load.kvar','Load.S1a',sigma=1.0),
        GaussianScale('load.kw','Load.S2b',sigma=2.0),
        GaussianScale('load.kvar','Load.S2b',sigma=1.0),
    ]
    if working:
        scales.extend((
            GaussianScale('pv.irradiance','PVSystem.PVD47',sigma=0.05),
            GaussianScale('pv.irradiance','PVSystem.PVD76',sigma=0.05),
        ))
    noise=ForecastNoiseSpec('additive_gaussian',seed=71,scales=tuple(scales))
    env=OpenDSSSimulator(FEEDERS/feeder/'IEEE123Master.dss',problem=problem(working),
        exogenous_replay=replay(tmp_path,working,mode),forecast_noise=noise,
        inventory_dir=tmp_path/'inv',semantic_registry_dir=tmp_path/'sem',
        preflight_dir=tmp_path/'pre')
    try:
        with pytest.raises(ControllerContextUnavailable):env.controller_context()
        backend=env._plant.backend
        original=backend.solve_snapshot; solves=[0]
        def counted():solves[0]+=1;return original()
        backend.solve_snapshot=counted
        obs,info=env.reset(seed=511)
        assert env.observation_space.contains(obs)
        assert solves[0]==1 and info['solution']['converged']
        access=SemanticRuntimeAccess(backend)
        before=float(access.read(NativePropertyAddress('Load.S1a','kW')))
        assert before==pytest.approx(32)
        original_write=backend.write_object_property
        def reject(*args,**kwargs):raise AssertionError('context mutated native physical state')
        backend.write_object_property=reject
        try:
            first=env.controller_context(forecast_horizon=2,required=True)
            second=env.controller_context(forecast_horizon=2,required=True)
            assert first==second and first.forecast==env.exogenous_forecast(2)
            assert first.observation_space_sha256 is not None
            assert first.action_space_sha256 is not None
            # A04 compiles semantic observations beneath the canonical ``current``
            # root. ``measure`` is only the selection-group label, not a Gym key.
            assert 'current' in first.observation
            assert first.observation['current']
            assert env.runtime_binding.observation_bindings
            for binding in env.runtime_binding.observation_bindings:
                assert binding.path[0] == 'current'
                actual_node = first.observation
                expected_node = obs
                for component in binding.path:
                    actual_node = actual_node[component]
                    expected_node = expected_node[component]
                np.testing.assert_array_equal(
                    np.asarray(actual_node), np.asarray(expected_node))
            assert first.static_network is not None
            # A02/AltDSS owns native element spelling; DSS identity is case-insensitive.
            # Compare the complete A05I6 static projection to the A02 inventory. A
            # genuinely missing switch (or filtered element) MUST still fail here.
            inv_elements = env.circuit_inventory.elements
            projected = first.static_network.elements
            expected_projection = tuple(
                (e.full_name, e.dss_class, int(e.num_phases), tuple(e.terminal_bus_specs))
                for e in inv_elements
            )
            actual_projection = tuple(
                (e.native_entity, e.dss_class, e.num_phases, e.terminal_bus_specs)
                for e in projected
            )
            assert actual_projection == expected_projection, 'STATIC_NETWORK_INVENTORY_PARITY_FAILED'
            switches = [e for e in projected if e.native_entity.casefold() == 'line.sw7']
            assert len(switches) == 1, (
                'SW7_MISSING_OR_DUPLICATE_IN_NATIVE_INVENTORY: '
                + repr(tuple(e.native_entity for e in projected if 'sw7' in e.native_entity.casefold()))
            )
            assert switches[0].dss_class.casefold() == 'line'
            assert switches[0].num_phases == 3
            assert len(switches[0].terminal_bus_specs) == 2
            assert first.static_network.inventory_semantic_sha256 == env.circuit_inventory.semantic_sha256
            assert first.last_realized_action_feedback==()
            assert first.decision_time_utc==info['time']['decision_time_utc']
            assert solves[0]==1
            assert all(v.forecast_mode=='synthetic_additive_gaussian' for v in first.forecast.values if v.channel_id=='load.kw')
            assert first.forecast.to_dict()==env.exogenous_forecast(2).to_dict()
            with pytest.raises(ControllerInformationError,match='DEVICE_NOT_AUTHORIZED'):
                env.controller_context(device_entities=('Load.S1a',))
            with pytest.raises(ControllerInformationError,match='FORECAST_SELECTORS'):
                env.controller_context(channel_ids=('load.kw',))
            if working:
                status=next(d for d in first.devices if d.native_entity.casefold()=='pvsystem.pvd47')
                assert status.health=='UNKNOWN' and status.present
                assert status.commandability in {'EXTERNAL_READY','UNKNOWN'}
            else:
                assert first.devices==()
            if mode=='strict':
                with pytest.raises(ForecastCoverageError):env.controller_context(forecast_horizon=3)
        finally:
            backend.write_object_property=original_write
        assert solves[0]==1 and float(access.read(NativePropertyAddress('Load.S1a','kW')))==pytest.approx(32)
        action=action_for(env,10.) if working else {}
        obs2,_,_,truncated,info2=env.step(action)
        assert not truncated and solves[0]==2 and env.observation_space.contains(obs2)
        after=env.controller_context(forecast_horizon=1)
        assert after.decision_time_utc==info2['time']['decision_time_utc']
        assert after.electrical_sample_time_utc==info2['time']['electrical_sample_time_utc']
        assert after.decision_time_utc!=after.electrical_sample_time_utc
        if working:
            assert after.last_realized_action_feedback[0]['status']=='ADMISSIBLE_APPLIED'
            assert float(access.read(NativePropertyAddress('PVSystem.PVD47','kvar')))==pytest.approx(10)
        assert solves[0]==2
        assert float(access.read(NativePropertyAddress('Load.S1a','kW')))==pytest.approx(32)
        _,_,_,truncated,info3=env.step(action_for(env,10.) if working else {})
        assert solves[0]==3
        assert float(access.read(NativePropertyAddress('Load.S1a','kW')))==pytest.approx(25)
        if mode=='strict':assert truncated
        with pytest.raises(ControllerContextUnavailable) if truncated else _nullcontext():
            env.controller_context()
    finally:env.close()


class _nullcontext:
    def __enter__(self):return None
    def __exit__(self,*args):return False
