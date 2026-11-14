"""P2 multi-fault graph restoration reference controller.

Frozen science: P2_Reconfiguration_Restoration_ControlScience_FROZEN.tex,
Block 6. Structural search and hard graph constraints are fully implemented;
electrical evaluation is a required, separately qualified, nonmutating callback
for any physical action. No simulator/backend access is used.
"""
from __future__ import annotations
from dataclasses import dataclass
from copy import deepcopy
from itertools import product
from math import isfinite
from typing import Callable,Mapping
import numpy as np
from .contracts import ControllerContractError, observed, bound_for, require_ready, encode_action

@dataclass(frozen=True)
class P2Load:
    native_entity:str
    bus:str
    priority:int
    curtailable:bool
    # available_kw must be taken from current authorized observation each step.
    def __post_init__(self):
        if self.priority not in (1,2,3,4):raise ControllerContractError('P2 priority outside 1..4')
        if not self.native_entity.casefold().startswith('load.') or not self.bus:
            raise ControllerContractError('Bad P2 load mapping')

@dataclass(frozen=True)
class P2Evaluation:
    """Result of an independently qualified controller-side current-state evaluator."""
    qualified:bool
    violation:float
    voltage_violation:float
    thermal_violation:float
    provenance:str

@dataclass(frozen=True)
class P2Decision:
    states:Mapping[str,bool]
    service:Mapping[str,float]
    score:tuple[float,int,float]
    diagnostics:Mapping[str,object]
    action:dict | None


def _bus(spec):return spec.split('.',1)[0].strip().casefold()

def _phase_disjoint_regulator_corridor(element):
    """Return a physical phase for a single-phase regulator on matching terminal phases.

    This is *only* a bus-level topological projection. It does not merge
    electrical elements, change a native DSS connection or certify per-phase
    restoration. Unknown/ambiguous terminal phases do not qualify for merging.
    """
    if element.dss_class.casefold() != 'transformer' or int(element.num_phases) != 1:
        return None
    specs=element.terminal_bus_specs
    if len(specs) != 2:
        return None
    phases=[]
    for spec in specs:
        parts=str(spec).strip().split('.')
        if len(parts)!=2 or parts[1] not in ('1','2','3'):
            return None
        phases.append(int(parts[1]))
    return phases[0] if phases[0]==phases[1] else None


def _graph(context,states:Mapping[str,bool],faults:set[str]):
    """Graph over physical terminal buses; no invented feeder branches."""
    net=context.static_network
    if net is None or not net.source_bus_candidates:
        raise ControllerContractError('Static network/source unavailable')
    adjacency={}
    edges=[]
    # Bus-level graph projection: distinct regulator phases on the *same*
    # two terminal buses are one physical corridor, not parallel cycles.
    # Overlapping phase duplicates, distinct lines and other equipment are
    # never merged and still constitute true parallel-path cycles.
    phase_corridor={}
    for e in net.elements:
        name=e.native_entity.casefold();cl=e.dss_class.casefold()
        if cl not in ('line','transformer','autotrans') or name in faults:
            continue
        buses=tuple(dict.fromkeys(_bus(x) for x in e.terminal_bus_specs))
        if len(buses)<2:continue
        if name in states and not states[name]:continue
        if len(buses)>2:raise ControllerContractError('Multi-terminal edge requires explicit graph model')
        a,b=buses[0],buses[1]
        if a==b:continue
        phase=_phase_disjoint_regulator_corridor(e)
        if phase is not None:
            corridor=tuple(sorted((a,b)))
            existing=phase_corridor.setdefault(corridor,set())
            if existing and phase not in existing:
                existing.add(phase)
                continue
            existing.add(phase)
        edges.append((a,b,name))
        adjacency.setdefault(a,[]).append((b,name))
        adjacency.setdefault(b,[]).append((a,name))
    sources={_bus(b) for b in net.source_bus_candidates}
    energized=set(sources);stack=list(sources)
    while stack:
        u=stack.pop()
        for v,_ in adjacency.get(u,()):
            if v not in energized:
                energized.add(v);stack.append(v)
    # For strict radiality, count energized graph edges and vertices in each
    # source-connected component. Disconnected cycles do not constitute an
    # energized cycle, but cannot be used for restoration.
    parent={x:x for x in energized}
    def root(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]];x=parent[x]
        return x
    for a,b,_ in edges:
        if a not in energized or b not in energized:continue
        ra,rb=root(a),root(b)
        if ra==rb:return energized,False
        parent[ra]=rb
    return energized,True

class P2GraphController:
    def __init__(self,*,loads:tuple[P2Load,...],faulted:tuple[str,...],
                 evaluator:Callable[[Mapping[str,bool],Mapping[str,float],object],P2Evaluation]|None=None,
                 max_candidates:int=4096):
        if len({x.native_entity.casefold() for x in loads})!=len(loads):
            raise ControllerContractError('Duplicate P2 load')
        if not faulted or max_candidates<1:
            raise ControllerContractError('P2 requires explicit faults and bounded search')
        self.loads=loads
        self.faulted={x.casefold() for x in faulted}
        self.evaluator=evaluator
        self.max_candidates=max_candidates
        self.last_successful_command=None
        self.last_episode=None

    def _present_loads(self,ctx):
        values={}
        for load in self.loads:
            try: p=float(observed(ctx,load.native_entity,'load_available_active_demand_kw'))
            except ControllerContractError as e:raise ControllerContractError('P2 missing current load demand: '+load.native_entity) from e
            if not isfinite(p) or p<0:raise ControllerContractError('P2 invalid present load demand')
            values[load.native_entity.casefold()]=p
        return values

    def _switch_current(self,ctx):
        states={};spelling={}
        for item in ctx.action_layout:
            path=item['path']
            if path[2]!='branch_switch_command':continue
            entity=path[0]+'.'+path[1]; name=entity.casefold()
            # Faulted switches are still in the full P2 action vector but must remain OPEN.
            if name not in self.faulted:require_ready(ctx,entity)
            raw=np.asarray(observed(ctx,entity,'branch_open_state')).reshape(-1)
            if raw.size==0 or not np.all((raw==0)|(raw==1)):
                raise ControllerContractError('Missing native switch-state evidence: '+entity)
            # Any open terminal disconnects the circuit edge.
            states[name]=not bool(np.any(raw))
            spelling[name]=entity
        if not states:raise ControllerContractError('P2 has no selected switch actions')
        return states,spelling

    def _structural(self,ctx):
        present=self._present_loads(ctx)
        current,spelling=self._switch_current(ctx)
        if not self.faulted.issubset({e.native_entity.casefold() for e in ctx.static_network.elements}):
            raise ControllerContractError('Fault not in authoritative static network')
        fixed={name:False for name in current if name in self.faulted}
        movable=tuple(sorted(name for name in current if name not in fixed))
        n=1<<len(movable)
        if n>self.max_candidates:
            raise ControllerContractError(f'P2 bounded enumeration exceeded: {n}')
        admissible=[]
        for values in product((False,True),repeat=len(movable)):
            states={**fixed,**dict(zip(movable,values))}
            energized,radial=_graph(ctx,states,self.faulted)
            if not radial:continue
            served={ld.native_entity:float(ld.bus.casefold() in energized) for ld in self.loads}
            score=sum(ld.priority*present[ld.native_entity.casefold()]*served[ld.native_entity] for ld in self.loads)
            changes=sum(states[k]!=current[k] for k in current)
            admissible.append(((-score,changes,tuple(int(states[k]) for k in sorted(states))),states,served,energized,score,changes))
        if not admissible:raise ControllerContractError('No radial candidate for current fault scenario')
        admissible.sort(key=lambda item:item[0])
        return admissible,current,spelling,present

    def preview(self,ctx):
        """Structural-only evidence. Absolutely no env.step action is emitted."""
        candidates,_,_,_=self._structural(ctx)
        first=candidates[0]
        return P2Decision(first[1],first[2],(first[4],-first[5],0.0),
            {'status':'STRUCTURAL_ONLY_NOT_ELECTRICALLY_QUALIFIED',
             'radial_candidates':len(candidates),'restored_weighted_kw':first[4],
             'switching_changes':first[5]},None)

    def _evaluate(self,ctx,states,service):
        value=self.evaluator(states,service,ctx)
        if not isinstance(value,P2Evaluation) or not value.qualified or not value.provenance:
            raise ControllerContractError('P2 evaluator missing qualification/provenance')
        if not all(isfinite(x) and x>=0 for x in (value.violation,value.voltage_violation,value.thermal_violation)):
            raise ControllerContractError('P2 evaluator invalid violation metrics')
        return value

    def _curtail(self,ctx,states,served,present):
        """Priority-ascending deterministic curtailment, with bounded bisection.

        The electrical evaluator owns nonmutating current-state physics. The
        decoder never infers that reducing P must help voltage; it explicitly
        re-evaluates every tentative reduction and rejects infeasible results.
        """
        fractions=dict(served)
        evaluation=self._evaluate(ctx,states,fractions)
        if evaluation.violation<=1e-10:return fractions,evaluation
        curtailable=sorted((ld for ld in self.loads if ld.curtailable and fractions[ld.native_entity]>0),
                 key=lambda x:(x.priority,-present[x.native_entity.casefold()],x.native_entity.casefold()))
        for load in curtailable:
            name=load.native_entity
            if present[name.casefold()]==0:continue
            # Bracket the least necessary single-load reduction under a
            # monotone-with-curtailment assumption, checked by evaluator calls.
            full=fractions[name]
            fractions[name]=0.
            at_zero=self._evaluate(ctx,states,fractions)
            if at_zero.violation>evaluation.violation+1e-9:
                fractions[name]=full  # curtailment worsens violation; do not invent relief
                continue
            if at_zero.violation>1e-10:
                evaluation=at_zero
                continue
            lo=0.;hi=full
            for _ in range(18):
                mid=(lo+hi)/2.
                fractions[name]=mid
                check=self._evaluate(ctx,states,fractions)
                if check.violation<=1e-10:lo=mid;at_zero=check
                else:hi=mid
            fractions[name]=lo
            return fractions,at_zero
        return fractions,evaluation

    def decide(self,ctx):
        """Complete full-vector command only if operational evaluation is qualified."""
        if self.evaluator is None:
            raise ControllerContractError('P2_ELECTRICAL_EVALUATOR_REQUIRED_BEFORE_ENV_STEP')
        if self.last_episode!=ctx.episode_id:
            self.last_episode=ctx.episode_id;self.last_successful_command=None
        candidates,current,spelling,present=self._structural(ctx)
        best=None
        for checked,(_,states,served,energized,restored,changes) in enumerate(candidates,1):
            service,evaluation=self._curtail(ctx,states,served,present)
            if evaluation.violation>1e-10:continue
            weighted=sum(ld.priority*present[ld.native_entity.casefold()]*service[ld.native_entity]
                         for ld in self.loads)
            voltage=evaluation.voltage_violation
            rank=(-weighted,changes,voltage,tuple(int(states[k]) for k in sorted(states)))
            if best is None or rank<best[0]:
                best=(rank,states,service,evaluation,checked,weighted,changes)
        if best is None:raise ControllerContractError('No electrically feasible candidate; refuse action')
        _,states,service,evaluation,checked,restored,changes=best
        commands={}
        for name,value in states.items():
            commands[(spelling[name],'branch_switch_command')]='CLOSED' if value else 'OPEN'
        for ld in self.loads:
            if not ld.curtailable:continue
            require_ready(ctx,ld.native_entity)
            commands[(ld.native_entity,'load_service_fraction')]=service[ld.native_entity]
        return P2Decision(states,service,(restored,-changes,-evaluation.voltage_violation),
            {'status':'CURRENT_STATE_ELECTRICALLY_EVALUATED','qualified_evaluator':evaluation.provenance,
             'candidates_checked':len(candidates),'radial_candidates':len(candidates),
             'restored_weighted_kw':restored,'switching_changes':changes},
            encode_action(ctx,commands))

    def on_success(self,ctx,decision,info):
        if decision.action is None or not info['solution']['converged'] or any(
                item['status'] not in ('ADMISSIBLE_APPLIED','FAULT_DISABLED')
                for item in info['action_audit']):
            raise ControllerContractError('No realized successful P2 action')
        self.last_successful_command=deepcopy(decision.action)

    def fallback(self,ctx,reason:str):
        if ctx.episode_id!=self.last_episode or self.last_successful_command is None:
            raise ControllerContractError('NO_SUCCESSFUL_P2_ACTION_AVAILABLE_FOR_FALLBACK')
        return deepcopy(self.last_successful_command), {'fallback':True,'reason':str(reason),'source':'last_successful_action'}
