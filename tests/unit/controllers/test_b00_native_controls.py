"""B00 controller contract tests; no electrical engine required."""
from types import SimpleNamespace as NS

import pytest

from opendsssim.controllers.baselines import NativeControlsBaseline, NativeBaselineContractError
from opendsssim.problem import ControlAuthorityMode


class Space:
    def __init__(self, allow=True): self.allow=allow
    def contains(self, value): return self.allow and value == {}


def test_empty_action_is_fresh_and_native_only():
    client=NativeControlsBaseline()
    a=client.action(context=NS(action_layout=()),action_space=Space())
    b=client.action(context=NS(action_layout=()),action_space=Space())
    assert a == b == {} and a is not b
    assert client.controller_id == 'B00.NATIVE_AS_INSTALLED.V01'


def test_reject_external_action_layout():
    with pytest.raises(NativeBaselineContractError,match='EXTERNAL_ACTION'):
        NativeControlsBaseline().action(context=NS(action_layout=({'entity':'PVSystem.X'},)),action_space=Space())


def test_reject_nonempty_or_invalid_action_space():
    with pytest.raises(NativeBaselineContractError,match='EMPTY_ACTION'):
        NativeControlsBaseline().action(context=NS(action_layout=()),action_space=Space(False))


def test_reject_missing_controller_context():
    with pytest.raises(NativeBaselineContractError,match='CONTEXT_REQUIRED'):
        NativeControlsBaseline().action(context=None,action_space=Space())


def test_source_is_native_only_without_actions():
    from experiments.pesgm2027.b00_native_controls.run_b00 import make_problem, PRE_FAULTS, PRIMARY
    for feeder in PRIMARY:
        p=make_problem(feeder)
        assert p.actions.groups == ()
        assert p.control_authority.mode is ControlAuthorityMode.NATIVE
        assert len(p.faults) == int(bool(PRE_FAULTS[feeder]))
    assert PRE_FAULTS['ieee123_p2_mf01_simple'] == ('Line.L45','Line.L77','Line.L93','Line.Sw7')
    assert PRE_FAULTS['ieee123_p2_mf02_exotic'] == ('Line.L45','Line.L77','Line.L93')


def test_unratified_feeder_rejected():
    from experiments.pesgm2027.b00_native_controls.run_b00 import make_problem, B00ExperimentError
    with pytest.raises(B00ExperimentError,match='UNRATIFIED'):
        make_problem('ieee123_p2_restoration')


def test_voltage_metrics_nonzero_and_raw_zero_distinguished():
    from experiments.pesgm2027.b00_native_controls.run_b00 import voltage_summary
    b=NS(entry=NS(quantity='bus_voltage_pu'),path=('current','Bus','A','bus_voltage_pu'))
    obs={'current':{'Bus':{'A':{'bus_voltage_pu':[0.0,0.949,1.06]}}}}
    report=voltage_summary(obs,(b,))
    assert report['zero_voltage_phase_count']==1
    assert report['outside_095_105_nonzero_count']==2
    assert report['min_nonzero_bus_phase_voltage_pu']==pytest.approx(.949)
    assert report['min_all_bus_phase_voltage_pu']==0.0


def test_replay_generation_loads_and_pv_provenance(tmp_path):
    from experiments.pesgm2027.b00_native_controls.run_b00 import make_replay, B00ExperimentError
    feeder=tmp_path/'ieee123_pesgm2027';feeder.mkdir()
    (feeder/'IEEE123Master.dss').write_text('Redirect IEEE123Loads.DSS\nRedirect PESGM2027_P1_PVSystems.dss\n')
    (feeder/'IEEE123Loads.DSS').write_text(''.join(f'New Load.L{i}\n' for i in range(91)))
    (feeder/'PESGM2027_P1_PVSystems.dss').write_text(''.join(f'New PVSystem.P{i}\n' for i in range(10)))
    replay, provenance=make_replay(feeder_dir=feeder,output_dir=tmp_path/'out',steps=2,
       start='2026-01-01T00:00:00Z',dt_seconds=3600,load_curve=(.75,1.0),pv_curve=(0,.8))
    assert len(replay.bindings)==2 and provenance['load_objects']==91 and provenance['pv_objects']==10
    assert provenance['profile_type'].startswith('SYNTHETIC')
    with pytest.raises(B00ExperimentError,match='LENGTH'):
        make_replay(feeder_dir=feeder,output_dir=tmp_path/'out2',steps=3,
             start='2026-01-01T00:00:00Z',dt_seconds=3600,load_curve=(1,),pv_curve=(.8,))
