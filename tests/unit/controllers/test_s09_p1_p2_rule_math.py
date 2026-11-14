"""Pure controller logic; stable deterministic baseline for P1/P2."""
from types import SimpleNamespace as NS
import numpy as np
import pytest
from opendsssim.controllers.reference import (
    P1Spec,P1Monitor,P1RuleBasedController,P2Load,P2GraphController,
    P2Evaluation,ControllerContractError)
from opendsssim.controllers.reference.p1_voltvar import pv_normalized_q

def layout(cls,name,quantity,space_type='Box',shape=(),low=-100.0,high=100.0,domain=()):
    return dict(path=[cls,name,quantity],space_type=space_type,shape=list(shape),low=low,high=high,domain_values=list(domain))

def mk_p1(voltage=1.0, cap_state=1.0, tap_state=1.025):
    return NS(episode_id='ep1',completed_steps=0,
       devices=tuple(NS(native_entity=e,commandability='EXTERNAL_READY') for e in ('PVSystem.pv','Capacitor.c','Transformer.reg')),
       action_layout=(layout('PVSystem','pv','pv_reactive_power_command',low=-100,high=100),
          layout('Capacitor','c','capacitor_state','MultiDiscrete',(1,),0,1,(0,1)),
          layout('Transformer','reg','transformer_tap_command',low=.9,high=1.1)),
       observation={'current':{'Bus':{'b':{'bus_voltage_pu':np.asarray([voltage,voltage])}},
          'Capacitor':{'c':{'capacitor_state':np.asarray([cap_state])}},
          'Transformer':{'reg':{'transformer_tap_position':np.asarray([1.,tap_state])}}}})

def test_p1_frozen_curve_every_breakpoint():
    spec=P1Spec({}, {}, {}, {})
    assert [pv_normalized_q(v,spec) for v in (.94,.95,.97,.99,1.,1.01,1.03,1.05,1.06)] == pytest.approx([1,1,.5,0,0,0,-.5,-1,-1])

def test_p1_simultaneous_cap_hysteresis_and_tap_semantics():
    spec=P1Spec(monitors={e:P1Monitor('b') for e in ('PVSystem.pv','Capacitor.c','Transformer.reg')},
        kva={'PVSystem.pv':5.},tap_step={'Transformer.reg':.00625},tap_winding_index={'Transformer.reg':1})
    ctrl=P1RuleBasedController(spec)
    action,diag=ctrl.decide(mk_p1(voltage=.96,cap_state=0),pv_available_kw={'PVSystem.pv':3.})
    assert action['PVSystem']['pv']['pv_reactive_power_command'] == pytest.approx(3.)
    assert action['Capacitor']['c']['capacitor_state'].tolist()==[1]
    assert action['Transformer']['reg']['transformer_tap_command'] == pytest.approx(1.03125)
    act2,_=ctrl.decide(mk_p1(voltage=1.,cap_state=1),pv_available_kw={'PVSystem.pv':3.})
    assert act2['Capacitor']['c']['capacitor_state'].tolist()==[1]
    assert act2['Transformer']['reg']['transformer_tap_command']==pytest.approx(1.025)
    act3,_=ctrl.decide(mk_p1(voltage=1.04,cap_state=1),pv_available_kw={'PVSystem.pv':3.})
    assert act3['Capacitor']['c']['capacitor_state'].tolist()==[0]
    assert act3['Transformer']['reg']['transformer_tap_command']==pytest.approx(1.01875)
    with pytest.raises(ControllerContractError,match='headroom'):
        ctrl.decide(mk_p1(),pv_available_kw={})

def mk_p2():
    elements=(NS(native_entity='Vsource.source',dss_class='Vsource',terminal_bus_specs=('source.1.2.3',),num_phases=3),
      NS(native_entity='Line.main',dss_class='Line',terminal_bus_specs=('source.1','a.1'),num_phases=1),
      NS(native_entity='Line.fault',dss_class='Line',terminal_bus_specs=('a.1','b.1'),num_phases=1),
      NS(native_entity='Line.s1',dss_class='Line',terminal_bus_specs=('a.1','b.1'),num_phases=1),
      NS(native_entity='Line.s2',dss_class='Line',terminal_bus_specs=('b.1','source.1'),num_phases=1))
    return NS(episode_id='ep1',devices=tuple(NS(native_entity='Line.'+s,commandability='EXTERNAL_READY') for s in ('s1','s2')),
      static_network=NS(source_bus_candidates=('source',), elements=elements),
      action_layout=(layout('Line','s1','branch_switch_command','Discrete',(),0,1,('OPEN','CLOSED')),
                     layout('Line','s2','branch_switch_command','Discrete',(),0,1,('OPEN','CLOSED'))),
      observation={'current':{'Line':{'s1':{'branch_open_state':np.asarray([1,1])},'s2':{'branch_open_state':np.asarray([1,1])}},
                               'Load':{'l1':{'load_available_active_demand_kw':10.},
                                       'l2':{'load_available_active_demand_kw':20.}}}})

def test_p2_radial_graph_search_and_evaluator_gate():
    loads=(P2Load('Load.l1','a',4,False),P2Load('Load.l2','b',1,False))
    c=P2GraphController(loads=loads,faulted=('Line.fault',))
    preview=c.preview(mk_p2())
    assert preview.action is None and preview.score[0]==60.0
    assert preview.diagnostics['status']=='STRUCTURAL_ONLY_NOT_ELECTRICALLY_QUALIFIED'
    with pytest.raises(ControllerContractError,match='ELECTRICAL_EVALUATOR_REQUIRED'):
        c.decide(mk_p2())
    c.evaluator=lambda states,service,ctx:P2Evaluation(True,0.,0.,0.,'TEST_ONLY_NO_PHYSICAL_CLAIM')
    choice=c.decide(mk_p2())
    assert choice.action is not None and sum(choice.states.values())==1
    assert choice.action['Line']['s1']['branch_switch_command'] in (0,1)
    assert choice.action['Line']['s2']['branch_switch_command'] in (0,1)
    # A false evaluator certificate fails closed.
    c.evaluator=lambda *args:P2Evaluation(False,0.,0.,0.,'')
    with pytest.raises(ControllerContractError,match='qualification'):
        c.decide(mk_p2())
