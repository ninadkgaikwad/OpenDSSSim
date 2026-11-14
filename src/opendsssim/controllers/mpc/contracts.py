"""Strict controller-side model data contracts for frozen P1/P2 LinDistFlow MPC.

No live backend/Plant object is imported or accepted here. All coefficients must
be supplied by a read-only circuit model compiler with verified provenance.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from math import isfinite
from typing import Mapping, Tuple

PhaseKey=tuple[str,int]

class MPCInputError(ValueError):
    pass


def _valid(x):
    return isinstance(x,(float,int)) and not isinstance(x,bool) and isfinite(float(x))

def _numbers(xs,length,label):
    if len(xs)!=length or any(not _valid(x) for x in xs):
        raise MPCInputError('NONFINITE_OR_WRONG_LENGTH:'+label)

def _key(key):
    return isinstance(key,tuple) and len(key)==2 and isinstance(key[0],str) and bool(key[0]) and key[1] in (1,2,3)


@dataclass(frozen=True)
class P1Branch:
    name:str
    parent:str
    child:str
    phases:tuple[int,...]
    r:tuple[tuple[float,...], ...]   # squared pu voltage per kW of per-phase flow
    x:tuple[tuple[float,...], ...]   # squared pu voltage per kvar of per-phase flow

@dataclass(frozen=True)
class P1PV:
    entity:str
    locations:tuple[PhaseKey,...]
    shares:tuple[float,...]
    kva:float
    available_kw:tuple[float,...]

@dataclass(frozen=True)
class P1Cap:
    entity:str
    locations:tuple[PhaseKey,...]  # physical-phase order = native action order
    kvar:tuple[float,...]          # per native phase/channel
    initial:tuple[int,...]

@dataclass(frozen=True)
class P1Tap:
    entity:str
    affects:tuple[tuple[str,int,float], ...]   # branch name, phase, voltage lift pu^2/index
    initial_index:int
    min_index:int
    max_index:int
    nominal_ratio:float
    step_ratio:float

@dataclass(frozen=True)
class P1Case:
    horizon:int
    nodes:tuple[PhaseKey,...]
    sources:Mapping[PhaseKey,tuple[float,...]]  # fixed squared per-unit voltage
    branches:tuple[P1Branch,...]
    loads_p:Mapping[PhaseKey,tuple[float,...]]
    loads_q:Mapping[PhaseKey,tuple[float,...]]
    pv:tuple[P1PV,...]
    capacitors:tuple[P1Cap,...]
    taps:tuple[P1Tap,...]
    vmin:float=0.95
    vmax:float=1.05
    w_voltage:float=1.0
    w_switch:float=0.1
    w_q:float=0.001
    w_slack:float=10000.0

    def validate(self):
        h=self.horizon
        if not isinstance(h,int) or not 1<=h<=96:raise MPCInputError('INVALID_P1_HORIZON')
        nodes=set(self.nodes)
        if not nodes or len(nodes)!=len(self.nodes) or any(not _key(n) for n in nodes):
            raise MPCInputError('INVALID_P1_NODES')
        if not self.sources or any(n not in nodes for n in self.sources):
            raise MPCInputError('P1_SOURCES_NOT_IN_NODES')
        for n,seq in self.sources.items():
            _numbers(seq,h,'P1_SOURCE_VOLTAGE')
            if any(v<=0 for v in seq):raise MPCInputError('NONPOSITIVE_SOURCE_VOLTAGE')
        if not (0<self.vmin<self.vmax<2):raise MPCInputError('INVALID_P1_VOLTAGE_BAND')
        for w in (self.w_voltage,self.w_switch,self.w_q,self.w_slack):
            if not _valid(w) or w<0:raise MPCInputError('INVALID_P1_WEIGHT')
        for loads in (self.loads_p,self.loads_q):
            for n,arr in loads.items():
                if n not in nodes:raise MPCInputError('LOAD_AT_UNKNOWN_PHASE')
                _numbers(arr,h,'LOAD_FORECAST')
        if {b.name.casefold() for b in self.branches}.__len__()!=len(self.branches):
            raise MPCInputError('DUPLICATE_P1_BRANCH')
        incoming={n:0 for n in nodes}
        for e in self.branches:
            if not e.name or e.parent==e.child or len(set(e.phases))!=len(e.phases) or not e.phases:
                raise MPCInputError('INVALID_P1_BRANCH')
            p=len(e.phases)
            if any(ph not in (1,2,3) or (e.parent,ph) not in nodes or (e.child,ph) not in nodes for ph in e.phases):
                raise MPCInputError('BRANCH_PHASE_MISSING')
            if len(e.r)!=p or len(e.x)!=p:raise MPCInputError('BRANCH_MATRIX_SHAPE')
            for row in e.r+e.x:_numbers(row,p,'BRANCH_MATRIX')
            for ph in e.phases:incoming[(e.child,ph)]+=1
        if any(incoming[n]!=0 for n in self.sources) or any(incoming[n]!=1 for n in nodes if n not in self.sources):
            raise MPCInputError('P1_NOT_RADIAL_PHASE_TREE')
        reached=set(self.sources)
        for _ in range(len(nodes)):
            for e in self.branches:
                for ph in e.phases:
                    if (e.parent,ph) in reached:reached.add((e.child,ph))
        if reached!=nodes:raise MPCInputError('P1_PHASE_SOURCE_DISCONNECTED')
        entities=[]
        for pv in self.pv:
            entities.append(pv.entity.casefold())
            if not pv.locations or any(n not in nodes for n in pv.locations):raise MPCInputError('INVALID_PV_LOCATION')
            _numbers(pv.shares,len(pv.locations),'PV_SHARES');_numbers(pv.available_kw,h,'PV_FORECAST')
            if abs(sum(pv.shares)-1)>1e-8 or any(s<0 for s in pv.shares):raise MPCInputError('INVALID_PV_ALLOCATION')
            if not _valid(pv.kva) or pv.kva<=0 or any(p<0 or p>pv.kva+1e-8 for p in pv.available_kw):raise MPCInputError('INVALID_PV_HEADROOM')
        for cap in self.capacitors:
            entities.append(cap.entity.casefold())
            if not cap.locations or len(set(cap.locations))!=len(cap.locations) or any(n not in nodes for n in cap.locations):raise MPCInputError('INVALID_CAP_LOCATION')
            _numbers(cap.kvar,len(cap.locations),'CAP_KVAR')
            if any(q<0 for q in cap.kvar) or len(cap.initial)!=len(cap.locations) or any(x not in (0,1) for x in cap.initial):raise MPCInputError('INVALID_CAP_STATE')
        bybranch={e.name.casefold():e for e in self.branches}
        for tap in self.taps:
            entities.append(tap.entity.casefold())
            if not tap.min_index<=tap.initial_index<=tap.max_index or not (0<tap.step_ratio<0.1) or tap.nominal_ratio<=0:
                raise MPCInputError('INVALID_TAP_RANGE')
            if not tap.affects:raise MPCInputError('MISSING_TAP_AFFECTS')
            for branch,ph,kappa in tap.affects:
                if branch.casefold() not in bybranch or ph not in bybranch[branch.casefold()].phases or not _valid(kappa):
                    raise MPCInputError('INVALID_TAP_INCIDENCE')
        if len(entities)!=len(set(entities)):raise MPCInputError('DUPLICATE_P1_DEVICE')
        return self

@dataclass(frozen=True)
class P2Branch:
    name:str
    a:str
    b:str
    phases:tuple[int,...]
    r:tuple[tuple[float,...], ...]
    x:tuple[tuple[float,...], ...]
    switch_entity:str|None=None
    healthy:bool=True
    smax_kva:tuple[float,...]|None=None

@dataclass(frozen=True)
class P2Load:
    entity:str
    bus:str
    phases:tuple[int,...]
    allocation:tuple[float,...]
    p_kw:tuple[float,...]
    q_kvar:tuple[float,...]
    priority:int
    curtailable:bool=False

@dataclass(frozen=True)
class P2Case:
    horizon:int
    buses:tuple[str,...]
    source_bus:str
    source_vsq:Mapping[int,tuple[float,...]]
    branches:tuple[P2Branch,...]
    loads:tuple[P2Load,...]
    initial_switches:Mapping[str,bool]
    voltage_only_exploratory:bool=False
    vmin:float=0.95
    vmax:float=1.05
    dt_hours:float=0.25
    voltage_big_m:float=10.0
    flow_multiplier:float=2.0
    switch_change_limit:int|None=None

    def validate(self):
        h=self.horizon
        if not isinstance(h,int) or not 1<=h<=96:raise MPCInputError('INVALID_P2_HORIZON')
        buses=set(self.buses)
        if not buses or len(buses)!=len(self.buses) or self.source_bus not in buses:raise MPCInputError('INVALID_P2_BUSES')
        if not self.source_vsq:raise MPCInputError('P2_SOURCE_PHASES_MISSING')
        for ph,arr in self.source_vsq.items():
            if ph not in (1,2,3):raise MPCInputError('INVALID_SOURCE_PHASE')
            _numbers(arr,h,'P2_SOURCE_VOLTAGE')
            if any(x<=0 for x in arr):raise MPCInputError('NONPOSITIVE_SOURCE_VOLTAGE')
        for val in (self.dt_hours,self.voltage_big_m,self.flow_multiplier):
            if not _valid(val) or val<=0:raise MPCInputError('INVALID_P2_SCALE')
        if not 0<self.vmin<self.vmax<2:raise MPCInputError('P2_VOLTAGE_BOUNDS')
        if self.switch_change_limit is not None and (not isinstance(self.switch_change_limit,int) or self.switch_change_limit<0):raise MPCInputError('BAD_SWITCH_CHANGE_LIMIT')
        sw=[];bn=[];seenphase=set()
        for e in self.branches:
            if not e.name or e.a==e.b or e.a not in buses or e.b not in buses or not e.phases or len(set(e.phases))!=len(e.phases):raise MPCInputError('BAD_P2_EDGE')
            bn.append(e.name.casefold());p=len(e.phases)
            if any(ph not in (1,2,3) for ph in e.phases) or len(e.r)!=p or len(e.x)!=p:raise MPCInputError('P2_MATRIX_SHAPE')
            for row in e.r+e.x:_numbers(row,p,'P2_BRANCH_MATRIX')
            if e.switch_entity is not None:
                sw.append(e.switch_entity.casefold())
                if e.switch_entity not in self.initial_switches:raise MPCInputError('MISSING_INITIAL_SWITCH')
            if e.smax_kva is None:
                if not self.voltage_only_exploratory:raise MPCInputError('P2_THERMAL_RATINGS_UNAVAILABLE')
            else:
                _numbers(e.smax_kva,p,'P2_THERMAL_CAPACITY')
                if any(x<=0 for x in e.smax_kva):raise MPCInputError('INVALID_THERMAL_RATING')
            seenphase.update((e.a,ph) for ph in e.phases); seenphase.update((e.b,ph) for ph in e.phases)
        if any(ph not in self.source_vsq for e in self.branches for ph in e.phases if e.a==self.source_bus or e.b==self.source_bus):
            raise MPCInputError('P2_SOURCE_PHASE_VOLTAGE_MISSING')
        if len(set(bn))!=len(bn) or len(set(sw))!=len(sw):raise MPCInputError('DUPLICATE_P2_EDGE')
        if set(x.casefold() for x in self.initial_switches)!=set(sw):raise MPCInputError('UNKNOWN_SWITCH_INITIAL')
        if any(not isinstance(val,bool) for val in self.initial_switches.values()):raise MPCInputError('BAD_INITIAL_SWITCH_VALUE')
        for load in self.loads:
            if load.bus not in buses or load.priority not in (1,2,3,4) or not load.phases or len(set(load.phases))!=len(load.phases):raise MPCInputError('INVALID_P2_LOAD')
            _numbers(load.allocation,len(load.phases),'LOAD_SHARES');_numbers(load.p_kw,h,'LOAD_P');_numbers(load.q_kvar,h,'LOAD_Q')
            if abs(sum(load.allocation)-1)>1e-8 or any(x<0 for x in load.allocation):raise MPCInputError('INVALID_LOAD_ALLOCATION')
            if any((load.bus,ph) not in seenphase for ph in load.phases):raise MPCInputError('LOAD_PHASE_NO_BRANCH')
            if any(p<0 for p in load.p_kw):raise MPCInputError('NEGATIVE_LOAD_P')
        if len({x.entity.casefold() for x in self.loads})!=len(self.loads):raise MPCInputError('DUPLICATE_LOAD')
        return self
