"""Native compile/reset smoke only; closed-loop/P2 science qualification is separate."""
from pathlib import Path
import pytest
from opendsssim.environment import OpenDSSSimulator
from opendsssim.controllers.reference import make_p1_problem, make_p2_problem

FEEDERS=Path(__file__).resolve().parents[2]/'experiments'/'pesgm2027'/'feeders'

def _get_devices(env,prefix,quantity):
    bundle=env._plant.semantic_registry
    ids=bundle.action_registry.entry_ids
    lookup=bundle.entry_by_id()
    return tuple(x.native_entity for i in ids if (x:=lookup[i]).quantity==quantity and x.native_entity is not None)

def test_s09_p1_external_action_contract_reset(tmp_path):
    # The S03 and S06 captures already proved the device family and fixed shapes.
    # This checks exactly the new RBC package's A04 contract, with no actions.
    env=OpenDSSSimulator(FEEDERS/'ieee123_pesgm2027'/'IEEE123Master.dss',
        inventory_dir=tmp_path/'iv0',semantic_registry_dir=tmp_path/'sem0',preflight_dir=tmp_path/'pf0')
    try:
        env.reset()
        pv=_get_devices(env,'PV','pv_reactive_power_command')
        caps=_get_devices(env,'Cap','capacitor_state')
        taps=_get_devices(env,'Tap','transformer_tap_command')
        assert (len(pv),len(caps),len(taps))==(10,4,7)
    finally:env.close()
    env=OpenDSSSimulator(FEEDERS/'ieee123_pesgm2027'/'IEEE123Master.dss',
        problem=make_p1_problem(pv=pv,capacitors=caps,transformers=taps),
        inventory_dir=tmp_path/'iv1',semantic_registry_dir=tmp_path/'sem1',preflight_dir=tmp_path/'pf1')
    try:
        obs,info=env.reset()
        assert info['solution']['converged'] and env.observation_space.contains(obs)
        assert len(env.controller_context().action_layout)==21
        assert len(env.runtime_binding.disabled_native_controls)>=1
    finally:env.close()

@pytest.mark.parametrize('feeder,faults,swcount',[
  ('ieee123_p2_mf01_simple',('Line.L45','Line.L77','Line.L93','Line.Sw7'),9),
  ('ieee123_p2_mf02_exotic',('Line.L45','Line.L77','Line.L93'),11),
])
def test_s09_p2_external_switch_contract_reset(tmp_path,feeder,faults,swcount):
    network=FEEDERS/feeder/'IEEE123Master.dss'
    baseline=OpenDSSSimulator(network,inventory_dir=tmp_path/'i0',semantic_registry_dir=tmp_path/'s0',preflight_dir=tmp_path/'p0')
    try:
        baseline.reset()
        switches=_get_devices(baseline,'Sw','branch_switch_command')
        assert len(switches)==swcount
    finally:baseline.close()
    env=OpenDSSSimulator(network,problem=make_p2_problem(switches=switches,curtailable_loads=(),faulted=faults),
        inventory_dir=tmp_path/'i1',semantic_registry_dir=tmp_path/'s1',preflight_dir=tmp_path/'p1')
    try:
        obs,info=env.reset()
        assert info['solution']['converged']
        assert env.observation_space.contains(obs)
        assert len(env.controller_context().action_layout)==swcount
    finally:env.close()
