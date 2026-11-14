"""P2MF01-R02 frozen formulation: multiphase P/Q declaration ordering.

An expression-tracking Gurobi test double verifies *construction only*, never
claims optimization; separate package qualification requires real Gurobi.
"""
from __future__ import annotations
import json, os, sys, types
from pathlib import Path
import pytest
from opendsssim.controllers.mpc.contracts import P2Branch, P2Case, P2Load
from opendsssim.controllers.mpc.closed_loop_a07a2 import p2_case_from_json
from opendsssim.controllers.mpc.p2_milp import solve_p2


class ModelBuilt(Exception):
    """Deliberately stops immediately when the real solver would be called."""


class Expr:
    def __init__(self, names=()):
        self.names=frozenset(names)
    def _combine(self, other):
        return Expr(self.names | (other.names if isinstance(other, Expr) else frozenset()))
    __add__=__sub__=__mul__=__le__=__ge__=__eq__=_combine
    __radd__=__rsub__=__rmul__=_combine


class ConstructionModel:
    def __init__(self, label):
        self.label=label
        self.Params=types.SimpleNamespace()
        self.vars={}
        self.constraints=[]
        self.objectives=[]
        self.optimize_called=False
    def addVar(self, *args, **kw):
        name=kw['name']
        if name in self.vars:raise AssertionError('DUPLICATE_VAR:'+name)
        v=self.vars[name]=Expr((name,))
        return v
    def addConstr(self, expr):
        self.constraints.append(expr)
        return expr
    def setObjectiveN(self, expr, index, **kwargs):
        self.objectives.append((index, expr, kwargs))
    def optimize(self):
        self.optimize_called=True
        raise ModelBuilt('MODEL_CONSTRUCTION_REACHED_OPTIMIZE')


def build_without_solving(case, monkeypatch):
    captured=[]
    def make(label):
        m=ConstructionModel(label)
        captured.append(m)
        return m
    gp=types.ModuleType('gurobipy')
    gp.GRB=types.SimpleNamespace(BINARY='BINARY', MINIMIZE=1)
    gp.Model=make
    gp.quicksum=lambda xs:sum(xs, 0)
    with monkeypatch.context() as scope:
        scope.setitem(sys.modules,'gurobipy',gp)
        with pytest.raises(ModelBuilt,match='MODEL_CONSTRUCTION_REACHED_OPTIMIZE'):
            solve_p2(case,time_limit_s=4.,threads=1)
    assert len(captured)==1
    model=captured[0]
    assert model.optimize_called
    assert len(model.objectives)==3
    return model


def tiny_case(phases=(1,2,3), thermal=False):
    phases=tuple(phases); h=2; size=len(phases)
    r=tuple(tuple(.0002 if i==j else .00005 for j in range(size)) for i in range(size))
    x=tuple(tuple(.0004 if i==j else .00006 for j in range(size)) for i in range(size))
    return P2Case(h,('s','a'),'s',{ph:(1.,1.) for ph in phases},
       (P2Branch('Line.l10','s','a',phases,r,x,None,True,
                 (120.,)*size if thermal else None),),
       (P2Load('Load.one','a',phases,(1./size,)*size,(20.,20.),(8.,8.),1,False),),
       {},voltage_only_exploratory=not thermal).validate()


def test_01_three_phase_drop_references_complete_pq_matrix(monkeypatch):
    case=tiny_case();m=build_without_solving(case,monkeypatch)
    for k in range(2):
        for ph in (1,2,3):
            need={f'P[Line.l10,{j},{k}]' for j in (1,2,3)} | {
                  f'Q[Line.l10,{j},{k}]' for j in (1,2,3)}
            paired=[c for c in m.constraints if need.issubset(c.names) and
                    f"v[('s', {ph}),{k}]" in c.names and
                    f"v[('a', {ph}),{k}]" in c.names]
            assert len(paired)==2,(k,ph,len(paired))
    assert sum(name.startswith('P[Line.l10,') for name in m.vars)==6
    assert sum(name.startswith('Q[Line.l10,') for name in m.vars)==6


def test_02_two_phase_drop_construction(monkeypatch):
    m=build_without_solving(tiny_case((1,3)),monkeypatch)
    assert sum(name.startswith('P[Line.l10,') for name in m.vars)==4
    assert sum(name.startswith('Q[Line.l10,') for name in m.vars)==4


def test_03_single_phase_rated_thermal_facets_preserved(monkeypatch):
    m=build_without_solving(tiny_case((2,),thermal=True),monkeypatch)
    assert 'sSlack[Line.l10,2,0]' in m.vars
    assert 'sSlack[Line.l10,2,1]' in m.vars
    for k in (0,1):
        p=f'P[Line.l10,2,{k}]'
        q=f'Q[Line.l10,2,{k}]'
        # 8 thermally rated octagonal facets at every horizon step.
        assert sum(p in c.names and q in c.names and
                   f'sSlack[Line.l10,2,{k}]' in c.names for c in m.constraints)==8


def baseline_case(name):
    root=Path(os.environ['MPC_A07A2_BASELINE_ROOT'])
    d=json.loads((root/'cases'/f'{name}_lindist_case.json').read_text(encoding='utf8'))
    return p2_case_from_json(d)


def test_04_mf01_native_capture_constructs_until_optimizer(monkeypatch):
    case=baseline_case('ieee123_p2_mf01_simple')
    assert case.horizon==2 and len(case.branches)==132 and len(case.loads)==91
    l10=next(e for e in case.branches if e.name.casefold()=='line.l10')
    assert len(l10.phases)==3
    m=build_without_solving(case,monkeypatch)
    assert len([x for x in m.vars if x.startswith('P[Line.l10,')])==6


def test_05_mf02_native_capture_constructs_until_optimizer(monkeypatch):
    case=baseline_case('ieee123_p2_mf02_exotic')
    assert case.horizon==2 and len(case.branches)==134 and len(case.loads)==91
    m=build_without_solving(case,monkeypatch)
    assert len(m.vars)>1000
