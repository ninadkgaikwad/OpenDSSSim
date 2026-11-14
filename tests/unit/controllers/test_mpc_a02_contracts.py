import pytest
from opendsssim.controllers.mpc import (P1Case,P1Branch,P1PV,P1Cap,P1Tap,
 P2Case,P2Branch,P2Load,MPCInputError,solve_p1,solve_p2,MPCSolveError)


def p1_case():
 return P1Case(2,(('s',1),('a',1)),{('s',1):(1.,1.)},
  (P1Branch('e','s','a',(1,),((.0002,),),((.0004,),)),),
  {('a',1):(20.,24.)},{('a',1):(9.,10.)},
  (P1PV('PVSystem.p',(('a',1),),(1.,),15.,(12.,12.)),),
  (P1Cap('Capacitor.c',(('a',1),),(5.,),(0,)),),
  (P1Tap('Transformer.r',(('e',1,.0125),),0,-2,2,1.,.00625),))

def p2_case(rated=True):
 return P2Case(2,('s','a','b'),'s',{1:(1.,1.)},
  (P2Branch('e1','s','a',(1,),((.0002,),),((.0002,),),None,True,(120.,) if rated else None),
   P2Branch('e2','a','b',(1,),((.0002,),),((.0002,),),'Line.sw1',True,(120.,) if rated else None)),
  (P2Load('Load.x','b',(1,),(1.,),(20.,20.),(8.,8.),1,False),),
  {'Line.sw1':False},voltage_only_exploratory=not rated)

def test_p1_structural_contract():
 assert p1_case().validate() is not None
 from dataclasses import replace
 with pytest.raises(MPCInputError, match='P1_NOT_RADIAL_PHASE_TREE'):
  replace(p1_case(),branches=()).validate()
 with pytest.raises(MPCInputError,match='INVALID_PV_HEADROOM'):
  replace(p1_case(),pv=(P1PV('PVSystem.p',(('a',1),),(1.,),15.,(16.,12.)),)).validate()

def test_p2_contract_fails_closed_missing_ratings():
 p2_case(True).validate()
 with pytest.raises(MPCInputError,match='P2_THERMAL_RATINGS_UNAVAILABLE'):
  from dataclasses import replace
  replace(p2_case(False),voltage_only_exploratory=False).validate()
 assert p2_case(False).validate().voltage_only_exploratory

def test_p2_fault_and_service_inputs():
 from dataclasses import replace
 e=p2_case().branches[1]
 c=replace(p2_case(),branches=(p2_case().branches[0],replace(e,healthy=False)))
 assert c.validate().branches[-1].healthy is False
 with pytest.raises(MPCInputError,match='MISSING_INITIAL_SWITCH'):
  replace(p2_case(),initial_switches={'Line.nosuch':False}).validate()

def test_no_gurobi_is_explicitly_reported():
 import importlib.util
 if importlib.util.find_spec('gurobipy') is not None:pytest.skip('Gurobi installed; solver tests run separately')
 with pytest.raises(MPCSolveError,match='GUROBIPY_NOT_AVAILABLE'):solve_p1(p1_case())
 with pytest.raises(MPCSolveError,match='GUROBIPY_NOT_AVAILABLE'):solve_p2(p2_case())
