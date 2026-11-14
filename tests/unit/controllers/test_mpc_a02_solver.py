"""Real Gurobi optimizer smoke tests: never replaced by a fake solver."""
import pytest
from test_mpc_a02_contracts import p1_case, p2_case
from opendsssim.controllers.mpc import solve_p1, solve_p2

gp=pytest.importorskip('gurobipy')

def test_p1_miqp_real_gurobi():
 r=solve_p1(p1_case(),time_limit_s=15.,threads=1)
 assert r.status=='OPTIMAL'
 assert len(r.pv_kvar)==1 and len(r.cap_states)==1 and len(r.tap_ratios)==1
 assert -9.0001<r.pv_kvar['PVSystem.p']<9.0001
 assert r.cap_states['Capacitor.c'] in ((0,),(1,))
 assert abs(r.tap_ratios['Transformer.r']-1.)<=.006251

def test_p2_milp_real_gurobi_restores_load():
 r=solve_p2(p2_case(),time_limit_s=30.,threads=1)
 assert r.status=='OPTIMAL'
 assert r.switches=={'Line.sw1':True}
 assert r.predicted_energized_buses==('a','b','s')
 assert abs(r.objectives['weighted_unserved_kwh'])<1e-7
 assert not r.diagnostics['bus_level_radiality_only'] is False

def test_p2_fault_must_remain_open():
 from dataclasses import replace
 c=p2_case();e=c.branches[1]
 c=replace(c,branches=(c.branches[0],replace(e,healthy=False)))
 r=solve_p2(c,time_limit_s=30.,threads=1)
 assert r.status=='OPTIMAL'
 assert r.switches['Line.sw1'] is False
 assert 'b' not in r.predicted_energized_buses
