"""Isolated A07A2 math/contract tests. No OpenDSSSim/AltDSS native import.
Use python <this file> with MPC_A07A2_BASELINE_ROOT set.
"""
from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import sys
import types
import unittest
from dataclasses import replace

ROOT=Path(os.environ['MPC_A07A2_BASELINE_ROOT'])
SOURCE=Path(os.environ['MPC_A07A2_CONTROLLER_SOURCE'])
REPO_SRC=Path(os.environ['MPC_A07A2_REPO_SRC'])
for name,folder in [('opendsssim',REPO_SRC/'opendsssim'),
                    ('opendsssim.controllers',REPO_SRC/'opendsssim'/'controllers'),
                    ('opendsssim.controllers.mpc',REPO_SRC/'opendsssim'/'controllers'/'mpc')]:
    mod=types.ModuleType(name);mod.__path__=[str(folder)];sys.modules[name]=mod
# Allow only the published helper signatures, not the physical backend.
ref=types.ModuleType('opendsssim.controllers.reference.contracts')
class ContractError(ValueError):pass
ref.ControllerContractError=ContractError
def observed(ctx,entity,quantity):
    cls,obj=entity.split('.',1)
    return ctx.observation['current'][cls.casefold()][obj.casefold()][quantity]
def ready(ctx,entity):
    if entity.casefold() not in {x.native_entity.casefold() for x in ctx.devices}:
        raise ContractError('not authorized')
def bound_for(ctx,entity,quantity):
    return next(x for x in ctx.action_layout if (x['path'][0]+'.'+x['path'][1]).casefold()==entity.casefold() and x['path'][2]==quantity)
ref.observed=observed;ref.require_ready=ready;ref.bound_for=bound_for
ref.encode_action=lambda ctx,commands: {'encoded':commands}
sys.modules['opendsssim.controllers.reference']=types.ModuleType('opendsssim.controllers.reference')
sys.modules['opendsssim.controllers.reference.contracts']=ref
spec=importlib.util.spec_from_file_location('opendsssim.controllers.mpc.closed_loop_a07a2',str(SOURCE))
mpc=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mpc;spec.loader.exec_module(mpc)
from opendsssim.controllers.mpc.p1_miqp import P1MPCResult
from opendsssim.controllers.mpc.p2_milp import P2MPCResult

def cases():
    return {name:json.loads((ROOT/'cases'/(name+'_lindist_case.json')).read_text())
            for name in ('ieee123_pesgm2027','ieee123_p2_mf01_simple','ieee123_p2_mf02_exotic')}

class Context:
    def __init__(self,case):
        self.episode_id='episode-000001';self.completed_steps=0;self.forecast=None
        self.decision_time_utc='2026-01-01T00:00:00+00:00';self.electrical_sample_time_utc=self.decision_time_utc
        self.action_space_sha256='A'*64;self.observation_space_sha256='B'*64
        self.action_layout=[]; self.devices=[]; obs={};obs['bus']={'150':{'bus_voltage_pu':[1.,1.,1.]}}
        from types import SimpleNamespace
        self.static_network=SimpleNamespace(inventory_semantic_sha256='C'*64)
        def add(e,q,shape=()):
            cls,obj=e.split('.',1);name=cls.lower();node=obs.setdefault(name,{})
            node.setdefault(obj.lower(),{})
            self.action_layout.append({'path':(cls,obj,q),'shape':shape,'space_type':'Box','low':None,'high':None})
            self.devices.append(SimpleNamespace(native_entity=e,commandability='EXTERNAL_READY'))
            return node[obj.lower()]
        if isinstance(case,mpc.P1Case):
            for p in case.pv:add(p.entity,'pv_reactive_power_command')
            for c in case.capacitors:
                node=add(c.entity,'capacitor_state',(1,));node['capacitor_state']=[1]
            for t in case.taps:
                node=add(t.entity,'transformer_tap_command');node['transformer_tap_position']=[1.,1.+t.initial_index*t.step_ratio]
        else:
            for e,initial in case.initial_switches.items():
                node=add(e,'branch_switch_command')
                node['branch_open_state']=[0 if initial else 1]
            for l in case.loads:
                cls,obj=l.entity.split('.',1)
                obs.setdefault(cls.lower(),{})[obj.lower()]={
                    'load_available_active_demand_kw':l.p_kw[0],
                    'load_available_reactive_demand_kvar':l.q_kvar[0]}
        self.observation={'current':obs}

class A07Isolated(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw=cases()
        cls.p1=mpc.p1_case_from_json(raw['ieee123_pesgm2027'])
        cls.p2a=mpc.p2_case_from_json(raw['ieee123_p2_mf01_simple'])
        cls.p2b=mpc.p2_case_from_json(raw['ieee123_p2_mf02_exotic'])
    def test01_native_models(self):
        self.assertEqual((len(self.p1.nodes),len(self.p2a.buses),len(self.p2b.buses)),(278,130,131))
    def test02_p1_context_update(self):
        c=Context(self.p1)
        x,n=mpc.update_p1(self.p1,c,pv_reference_irradiance={p.entity:1. for p in self.p1.pv})
        self.assertEqual(len(x.capacitors),4);self.assertEqual(x.capacitors[0].initial,(1,1,1))
        self.assertIn('PERSISTENCE',n['forecast_mode'])
    def test03_p2a_context_update(self):
        x,n=mpc.update_p2(self.p2a,Context(self.p2a))
        self.assertEqual(len(x.loads),91);self.assertFalse(x.initial_switches['Line.sw7'])
    def test04_p2b_context_update(self):
        x,n=mpc.update_p2(self.p2b,Context(self.p2b))
        self.assertEqual(len(x.loads),91);self.assertFalse(x.initial_switches['Line.sw7'])
    def test05_reject_missing_source_voltage(self):
        c=Context(self.p1);del c.observation['current']['bus']['150']
        with self.assertRaises(Exception):mpc.update_p1(self.p1,c,pv_reference_irradiance={})
    def test06_reject_missing_p2_demand(self):
        c=Context(self.p2a);del c.observation['current']['load']['s100c']
        with self.assertRaises(Exception):mpc.update_p2(self.p2a,c)
    def test07_reject_missing_action(self):
        c=Context(self.p1);c.action_layout.pop()
        with self.assertRaisesRegex(mpc.ClosedLoopContractError,'ACTION_MODEL_SET_MISMATCH'):
            mpc.update_p1(self.p1,c,pv_reference_irradiance={})
    def test08_reject_cap_state_disagreement(self):
        c=Context(self.p1);c.observation['current']['capacitor']['c83']['capacitor_state']=[1,0,1]
        with self.assertRaisesRegex(mpc.ClosedLoopContractError,'CAP_SHARED'):
            mpc.update_p1(self.p1,c,pv_reference_irradiance={})
    def test09_case_insensitive_p1_action(self):
        r=P1MPCResult('OPTIMAL',0.,0.,{x.entity.upper():0. for x in self.p1.pv},
            {x.entity.upper():tuple(1 for _ in x.locations) for x in self.p1.capacitors},
            {x.entity.upper():1. for x in self.p1.taps},{})
        a=mpc.p1_action(Context(self.p1),r)
        self.assertIn('encoded',a);self.assertEqual(len(a['encoded']),21)
    def test10_reject_incompatible_cap_phase_action(self):
        states={x.entity:tuple(1 for _ in x.locations) for x in self.p1.capacitors}
        states[self.p1.capacitors[0].entity]=(1,0,1)
        r=P1MPCResult('OPTIMAL',0.,0.,{x.entity:0. for x in self.p1.pv},states,
           {x.entity:1. for x in self.p1.taps},{})
        with self.assertRaisesRegex(mpc.ClosedLoopContractError,'INCOMPATIBLE_CAP'):
            mpc.p1_action(Context(self.p1),r)
    def test11_p2_action_names(self):
        r=P2MPCResult('OPTIMAL',{x.upper():bool(v) for x,v in self.p2a.initial_switches.items()},(),(),{}, {})
        # Named load_service must be a mapping (P2 has zero curtailable channels).
        r=replace(r,load_service={})
        a=mpc.p2_action(Context(self.p2a),r)
        self.assertIn('encoded',a)
    def test12_p2_fault_overrides_open_readback(self):
        c=Context(self.p2a);c.observation['current']['line']['sw7']['branch_open_state']=[0]
        x,_=mpc.update_p2(self.p2a,c);self.assertFalse(x.initial_switches['Line.sw7'])
    def test13_reject_wrong_forecast_identity(self):
        c=Context(self.p1)
        c.forecast=types.SimpleNamespace(status='AVAILABLE',horizon=12,episode_id='other',decision_index=0,values=())
        with self.assertRaisesRegex(mpc.ClosedLoopContractError,'IDENTITY'):
            mpc.update_p1(self.p1,c,pv_reference_irradiance={})
    def test14_source_authority(self):
        c=Context(self.p2a);c.observation['current']['bus']['150']['bus_voltage_pu']=[0,0,0]
        with self.assertRaisesRegex(mpc.ClosedLoopContractError,'BAD_SOURCE'):
            mpc.update_p2(self.p2a,c)
    def test15_p2_absolutely_no_thermal_claim(self):
        self.assertTrue(self.p2a.voltage_only_exploratory)
        self.assertTrue(all(e.smax_kva is None for e in self.p2a.branches))

if __name__=='__main__':unittest.main(verbosity=2)
