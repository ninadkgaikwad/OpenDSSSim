"""A07A3 capacitor bank/phase scientific regression tests.

The package qualifier *requires* a real Gurobi installation; no fake solver.
Only controller-side P1 model and frozen output-interface contracts tested.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import pytest
from opendsssim.controllers.mpc.contracts import P1Case, P1Branch, P1Cap, MPCInputError
from opendsssim.controllers.mpc.p1_miqp import solve_p1


def make_case(phases=(1,2,3),horizon=2,initial=None):
    phases=tuple(phases)
    if initial is None:initial=(1,)*len(phases)
    nodes=tuple((bus,ph) for bus in ('s','a') for ph in phases)
    p=len(phases)
    zero=tuple((0.,)*p for _ in phases)
    x=tuple(tuple(.0002 if i==j else 0. for j in range(p)) for i in range(p))
    return P1Case(
        horizon=horizon,nodes=nodes,
        sources={('s',ph):(1.,)*horizon for ph in phases},
        branches=(P1Branch('Line.e','s','a',phases,zero,x),),
        loads_p={},loads_q={},pv=(),
        capacitors=(P1Cap('Capacitor.c',tuple(('a',ph) for ph in phases),
                           tuple(10. for _ in phases),tuple(initial)),),taps=(),
        w_voltage=1.,w_switch=.1,w_q=.001,w_slack=10000.).validate()


def test_01_three_phase_bank_is_one_device_in_ratified_model():
    """Static captured IEEE-123 fixture, not an inferred device count."""
    root=Path(os.environ['MPC_A07A2_BASELINE_ROOT'])
    data=json.loads((root/'cases/ieee123_pesgm2027_lindist_case.json').read_text())
    assert data['horizon']==12
    assert len(data['capacitors'])==4
    c83=next(c for c in data['capacitors'] if c['entity'].casefold()=='capacitor.c83')
    assert c83['locations']==[['83',1],['83',2],['83',3]]
    assert c83['kvar']==[200.,200.,200.]
    assert c83['initial']==[1,1,1]


def test_02_disagreeing_initial_phases_rejected_without_solver():
    case=make_case(initial=(1,0,1))
    with pytest.raises(MPCInputError,match='P1_SHARED_CAP_BANK_INITIAL_PHASE_DISAGREEMENT'):
        solve_p1(case)


def test_03_three_phase_one_bank_real_gurobi():
    import gurobipy  # MUST be real; fails if not installed, not skipped
    case=make_case(horizon=3)
    r=solve_p1(case,time_limit_s=30.,threads=1,output_flag=False)
    assert r.status=='OPTIMAL'
    assert r.cap_states['Capacitor.c'] in ((0,0,0),(1,1,1))
    assert r.diagnostics['capacitor_control_granularity']=='ONE_BINARY_PER_PHYSICAL_CAPACITOR_BANK_PER_STEP'
    assert r.diagnostics['capacitor_bank_binary_variables']==3
    assert r.diagnostics['capacitor_bank_switching_auxiliaries']==3
    assert r.diagnostics['capacitor_phase_injection_count']==3


def test_04_single_phase_one_bank_real_gurobi():
    import gurobipy
    case=make_case(phases=(1,),horizon=2,initial=(0,))
    r=solve_p1(case,time_limit_s=30.,threads=1,output_flag=False)
    assert r.status=='OPTIMAL'
    assert r.cap_states['Capacitor.c'] in ((0,),(1,))
    assert r.diagnostics['capacitor_bank_binary_variables']==2
    assert r.diagnostics['capacitor_phase_injection_count']==1


def test_05_model_validation_keeps_phases_and_case_weights_unchanged():
    case=make_case()
    assert case.validate() is case
    assert len(case.nodes)==6 and len(case.branches)==1
    assert case.w_switch==.1 and case.w_slack==10000.
