"""Pure A05I6 controller-information snapshot and authorization checks."""
from dataclasses import FrozenInstanceError
from types import SimpleNamespace as NS
import pytest

from opendsssim.environment.controller_context import (
    ControllerInformationError, _freeze, build_controller_context,
)


class Clock:
    def metadata(self, *, phase, completed_steps):
        return dict(episode_id='ep-1', decision_time_utc=f'2026-01-01T{completed_steps:02d}:00:00Z',
                    electrical_sample_time_utc=f'2026-01-01T{max(completed_steps-1,0):02d}:00:00Z')


class Access:
    def __init__(self, enabled=True): self.enabled=enabled; self.reads=0
    def read(self, address):
        self.reads+=1
        if isinstance(self.enabled, Exception): raise self.enabled
        return self.enabled


class Inventory:
    circuit_name='test'
    semantic_sha256='HASH'
    buses=(NS(name='source',node_names=('source.1',)), NS(name='b',node_names=('b.1',)))
    objects=(NS(full_name='PVSystem.P1', dss_class='PVSystem',property_names=('Enabled','kvar')),
             NS(full_name='Load.L1', dss_class='Load',property_names=('Enabled',)))
    elements=(NS(full_name='Vsource.Source',dss_class='Vsource',num_phases=3,terminal_bus_specs=('source.1.2.3',)),
              NS(full_name='PVSystem.P1',dss_class='PVSystem',num_phases=3,terminal_bus_specs=('b.1.2.3',)))


def binding(faulted=()):
    b=NS(entry=NS(native_entity='PVSystem.P1'))
    return NS(observation_bindings=(),action_bindings=(b,),fault_targets=faulted,
              resolved_problem=NS(control_authority=NS(external_entities=('PVSystem.P1',))))


def build(*, enabled=True, faults=(), device_entities=None, static=True):
    obs={'p': {'x': [1.0, 2.0]}}
    access=Access(enabled)
    ctx=build_controller_context(clock=Clock(),completed_steps=1,observation=obs,
         compiled_spaces=None, runtime_binding=binding(faults), inventory=Inventory(),
         access=access, action_audits=(),forecast=None,device_entities=device_entities,
         include_static_network=static)
    return ctx,obs,access


def test_detached_immutable_observation_and_static_topology():
    ctx,obs,access=build()
    assert ctx.decision_time_utc != ctx.electrical_sample_time_utc
    assert ctx.observation['p']['x']==(1.0,2.0)
    with pytest.raises(TypeError):ctx.observation['new']=1
    with pytest.raises((TypeError,AttributeError)):ctx.observation['p']['x'][0]=999
    with pytest.raises(FrozenInstanceError):ctx.completed_steps=3
    obs['p']['x'][0]=999
    assert ctx.observation['p']['x'][0]==1.0
    detached=ctx.to_dict(); detached['observation']['p']['x'][0]=999
    assert ctx.to_dict()['observation']['p']['x'][0]==1.0
    assert ctx.static_network.source_bus_candidates==('source',)
    assert ctx.devices[0].health=='UNKNOWN'  # Enabled is not a health sensor
    assert ctx.devices[0].commandability=='EXTERNAL_READY'
    assert access.reads==1
    assert 'backend' not in ctx.to_dict()
    assert 'future_truth' not in str(ctx.to_dict())


@pytest.mark.parametrize('enabled,faults,expected',[
    (True,('PVSystem.P1',),'FAULT_LOCKED'),
    (False,(),'DISABLED'),
    (RuntimeError('no sensor'),(),'UNKNOWN'),
])
def test_health_not_fabricated_and_faults_preserved(enabled,faults,expected):
    ctx,_,_=build(enabled=enabled,faults=faults)
    assert ctx.devices[0].commandability==expected
    assert ctx.devices[0].health==('FAULTED' if faults else 'UNKNOWN')


def test_device_permission_is_enforced_before_native_reads():
    with pytest.raises(ControllerInformationError,match='NOT_AUTHORIZED'):
        build(device_entities=('Load.L1',))
    with pytest.raises(ControllerInformationError,match='DUPLICATE'):
        build(device_entities=('PVSystem.P1','pvsystem.p1'))
    ctx,_,access=build(device_entities=(),static=False)
    assert ctx.devices==() and ctx.static_network is None and access.reads==0


def test_nonfinite_and_unsupported_values_fail_closed():
    with pytest.raises(ControllerInformationError,match='NONFINITE'):
        _freeze({'value':float('nan')})
    with pytest.raises(ControllerInformationError,match='UNSUPPORTED'):
        _freeze({'hidden':object()})
