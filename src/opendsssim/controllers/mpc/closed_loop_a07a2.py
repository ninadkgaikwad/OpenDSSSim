"""A07A2 public-context-only P1/P2 receding-horizon integration.

No Plant/backend access. Static model matrices are prequalified offline AltDSS
snapshots; online state and eligible forecasts ONLY from ControllerContext.
Fail closed rather than project incompatible MIQP phase decisions or fault states.
"""
from __future__ import annotations
from dataclasses import replace
from math import isfinite
from typing import Mapping
import numpy as np
from .contracts import (P1Case, P1Branch, P1PV, P1Cap, P1Tap,
                        P2Case, P2Branch, P2Load, MPCInputError)

class ClosedLoopContractError(ValueError):
    pass


def _finite(raw, tag, lo=None, hi=None):
    try:
        x=float(raw)
    except (TypeError,ValueError) as exc:
        raise ClosedLoopContractError(tag) from exc
    if not isfinite(x) or (lo is not None and x<lo) or (hi is not None and x>hi):
        raise ClosedLoopContractError(tag)
    return x


def _ob(ctx, entity, quantity):
    from opendsssim.controllers.reference.contracts import observed
    return observed(ctx,entity,quantity)


def _vector(ctx, entity, quantity):
    a=np.asarray(_ob(ctx,entity,quantity),dtype=float).reshape(-1)
    if not a.size or not np.all(np.isfinite(a)):
        raise ClosedLoopContractError('BAD_CURRENT_OBSERVATION:'+entity+':'+quantity)
    return a


def _forecast(ctx,h):
    f=ctx.forecast
    if f is None or f.status!='AVAILABLE':
        return {}, 'NO_QUALIFIED_FORECAST__CURRENT_PERSISTENCE'
    if f.horizon!=h or f.episode_id!=ctx.episode_id or f.decision_index!=ctx.completed_steps:
        raise ClosedLoopContractError('FORECAST_DECISION_IDENTITY_MISMATCH')
    table={}
    for item in f.values:
        if item.lead_index<0 or item.lead_index>=h:
            raise ClosedLoopContractError('FORECAST_BAD_LEAD')
        key=(item.channel_id.casefold(),item.entity_id.casefold(),item.lead_index)
        if key in table:raise ClosedLoopContractError('FORECAST_DUPLICATE_CHANNEL')
        table[key]=_finite(item.value,'NONFINITE_FORECAST')
    return table, f.forecast_mode


def _series(table,channel,entity,h):
    keys=[(channel.casefold(),entity.casefold(),t) for t in range(h)]
    present=[k in table for k in keys]
    if any(present) and not all(present):raise ClosedLoopContractError('PARTIAL_FORECAST:'+channel+':'+entity)
    return tuple(table[k] for k in keys) if all(present) else None


def _source(ctx,bus,phases):
    a=_vector(ctx,'Bus.'+bus,'bus_voltage_pu')
    # Source is explicitly 3-phase in these frozen IEEE-123 cases. The ordered
    # A04 bus-node voltage vector follows native terminal phase order 1,2,3.
    if tuple(sorted(phases))!=(1,2,3) or a.size!=3:
        raise ClosedLoopContractError('UNQUALIFIED_SOURCE_PHASE_ORDER')
    if np.any(a<0.5) or np.any(a>1.5):raise ClosedLoopContractError('BAD_SOURCE_VOLTAGE_PU')
    return {int(ph):float(a[int(ph)-1]**2) for ph in phases}


def p1_case_from_json(d):
    if d.get('kind')!='P1Case':raise ClosedLoopContractError('WRONG_STATIC_P1_CASE')
    nodes=tuple((str(b),int(p)) for b,p in d['nodes'])
    sources={(str(s['bus']),int(s['phase'])):tuple(map(float,s['squared_pu'])) for s in d['sources']}
    branch=tuple(P1Branch(str(x['name']),str(x['parent']),str(x['child']),tuple(x['phases']),
           tuple(tuple(float(v) for v in row) for row in x['r']),
           tuple(tuple(float(v) for v in row) for row in x['x'])) for x in d['branches'])
    lp={(str(x['bus']),int(x['phase'])):tuple(map(float,x['p_kw'])) for x in d['loads']}
    lq={(str(x['bus']),int(x['phase'])):tuple(map(float,x['q_kvar'])) for x in d['loads']}
    pv=tuple(P1PV(x['entity'],tuple((str(b),int(ph)) for b,ph in x['locations']),
             tuple(map(float,x['shares'])),float(x['kva']),tuple(map(float,x['available_kw']))) for x in d['pv'])
    caps=tuple(P1Cap(x['entity'],tuple((str(b),int(ph)) for b,ph in x['locations']),
            tuple(map(float,x['kvar'])),tuple(int(y) for y in x['initial'])) for x in d['capacitors'])
    taps=tuple(P1Tap(x['entity'],tuple((str(n),int(ph),float(v)) for n,ph,v in x['affects']),
            int(x['initial_index']),int(x['min_index']),int(x['max_index']),
            float(x['nominal_ratio']),float(x['step_ratio'])) for x in d['taps'])
    c=P1Case(int(d['horizon']),nodes,sources,branch,lp,lq,pv,caps,taps,
        float(d['voltage_band'][0]),float(d['voltage_band'][1]),
        **{'w_'+k:float(v) for k,v in d['weights'].items()})
    return c.validate()


def p2_case_from_json(d):
    if d.get('kind')!='P2Case':raise ClosedLoopContractError('WRONG_STATIC_P2_CASE')
    branch=tuple(P2Branch(x['name'],x['a'],x['b'],tuple(x['phases']),
        tuple(tuple(float(v) for v in row) for row in x['r']),
        tuple(tuple(float(v) for v in row) for row in x['x']),
        x.get('switch_entity'),bool(x['healthy']),
        None if x.get('smax_kva') is None else tuple(map(float,x['smax_kva']))) for x in d['branches'])
    loads=tuple(P2Load(x['entity'],x['bus'],tuple(x['phases']),tuple(map(float,x['allocation'])),
          tuple(map(float,x['p_kw'])),tuple(map(float,x['q_kvar'])),int(x['priority']),
          bool(x['curtailable'])) for x in d['loads'])
    c=P2Case(int(d['horizon']),tuple(d['buses']),d['source_bus'],
       {int(k):tuple(map(float,v)) for k,v in d['source_vsq'].items()},
       branch,loads,{str(k):bool(v) for k,v in d['initial_switches'].items()},
       bool(d['voltage_only_exploratory']),float(d['vmin']),float(d['vmax']),float(d['dt_hours']))
    return c.validate()


def _check_layout(ctx,quantities):
    by={}
    for e in ctx.action_layout:
        if len(e['path'])!=3:raise ClosedLoopContractError('INVALID_PROBLEMSPEC_ACTION_PATH')
        cls,obj,q=e['path'];key=(cls+'.'+obj).casefold()
        if key in by:raise ClosedLoopContractError('DUPLICATE_PROBLEMSPEC_ACTION_ENTITY')
        if q not in quantities:raise ClosedLoopContractError('UNEXPECTED_PROBLEMSPEC_ACTION:'+q)
        by[key]=(cls+'.'+obj,q,e)
    if not by:raise ClosedLoopContractError('EMPTY_PROBLEMSPEC_ACTION_LAYOUT')
    return by


def update_p1(base:P1Case,ctx, *, pv_reference_irradiance:Mapping[str,float]):
    base.validate(); h=base.horizon
    layout=_check_layout(ctx,{'pv_reactive_power_command','capacitor_state','transformer_tap_command'})
    devices={x.entity.casefold():x for x in base.pv+base.capacitors+base.taps}
    if set(layout)!=set(devices):raise ClosedLoopContractError('P1_ACTION_MODEL_SET_MISMATCH')
    srcbus={n[0] for n in base.sources}
    if len(srcbus)!=1:raise ClosedLoopContractError('P1_NONUNIQUE_SOURCE_BUS')
    src=next(iter(srcbus)); v=_source(ctx,src,{n[1] for n in base.sources})
    sources={(src,ph):(vsq,)*h for ph,vsq in v.items()}
    f,fmode=_forecast(ctx,h)
    allmult=[]
    for t in range(h):
        vals=[vv for (channel,ent,k),vv in f.items() if channel=='load.multiplier' and k==t]
        if vals and (max(vals)-min(vals)>1.e-8):
            raise ClosedLoopContractError('P1_NONUNIFORM_LOAD_MULTIPLIER_NEEDS_PER_LOAD_MAPPING')
        allmult.append(vals[0] if vals else 1.0)
    if any(x<0 or x>3 for x in allmult):raise ClosedLoopContractError('P1_LOAD_MULTIPLIER_OUT_OF_DECLARED_RANGE')
    loads_p={n:tuple(seq[0]*allmult[t] for t in range(h)) for n,seq in base.loads_p.items()}
    loads_q={n:tuple(seq[0]*allmult[t] for t in range(h)) for n,seq in base.loads_q.items()}
    pv=[];pv_mode=[]
    for p in base.pv:
        z=layout[p.entity.casefold()]
        if z[1]!='pv_reactive_power_command':raise ClosedLoopContractError('P1_PV_ACTION_QUANTITY_MISMATCH')
        from opendsssim.controllers.reference.contracts import require_ready
        require_ready(ctx,z[0])
        g=_series(f,'pv.irradiance',p.entity,h)
        if g is None:
            seq=(float(p.available_kw[0]),)*h
            pv_mode.append('PERSISTENCE_OF_OFFLINE_NATIVE_PV_ACTIVE_POWER')
        else:
            ref=_finite(pv_reference_irradiance.get(p.entity.casefold()),'MISSING_PV_NATIVE_IRRADIANCE_REFERENCE',0.001)
            seq=tuple(min(float(p.kva),max(0.0,float(p.available_kw[0])*x/ref)) for x in g)
            pv_mode.append('QUALIFIED_IRRADIANCE_FORECAST_TO_P_APPROXIMATION')
        pv.append(replace(p,available_kw=seq))
    caps=[]
    for c in base.capacitors:
        name,q,e=layout[c.entity.casefold()]
        if q!='capacitor_state':raise ClosedLoopContractError('P1_CAP_ACTION_QUANTITY_MISMATCH')
        from opendsssim.controllers.reference.contracts import require_ready
        require_ready(ctx,name)
        native=_vector(ctx,name,'capacitor_state')
        if native.size not in (1,len(c.locations)) or np.any((native!=0)&(native!=1)) or len(set(native.tolist()))!=1:
            raise ClosedLoopContractError('P1_CAP_SHARED_BANK_STATE_UNQUALIFIED:'+name)
        caps.append(replace(c,initial=tuple([int(native[0])]*len(c.locations))))
    taps=[]
    for t in base.taps:
        name,q,e=layout[t.entity.casefold()]
        if q!='transformer_tap_command':raise ClosedLoopContractError('P1_TAP_ACTION_QUANTITY_MISMATCH')
        from opendsssim.controllers.reference.contracts import require_ready
        require_ready(ctx,name)
        raw=_vector(ctx,name,'transformer_tap_position')
        if raw.size!=2:raise ClosedLoopContractError('P1_TAP_WINDING_SHAPE_NOT_QUALIFIED:'+name)
        idx=int(round((float(raw[1])-t.nominal_ratio)/t.step_ratio))
        if idx<t.min_index or idx>t.max_index or abs(raw[1]-(t.nominal_ratio+t.step_ratio*idx))>1e-3:
            raise ClosedLoopContractError('P1_TAP_READBACK_OFF_DISCRETE_GRID:'+name)
        taps.append(replace(t,initial_index=idx))
    out=replace(base,sources=sources,loads_p=loads_p,loads_q=loads_q,pv=tuple(pv),
                capacitors=tuple(caps),taps=tuple(taps)).validate()
    return out,{'forecast_mode':fmode,'load_multiplier':allmult,
                'pv_forecast_mapping':sorted(set(pv_mode)),
                'current_capacitor_states':'AUTHORIZED_PROBLEMSPEC_OBSERVATION',
                'current_tap_states':'AUTHORIZED_PROBLEMSPEC_OBSERVATION',
                'source_voltage':'AUTHORIZED_PROBLEMSPEC_BUS_OBSERVATION',
                'pv_current_power':'OFFLINE_ALTDSS_REFERENCE_NOT_LIVE_ELECTRICAL_P'}


def update_p2(base:P2Case,ctx):
    base.validate(); h=base.horizon
    layout=_check_layout(ctx,{'branch_switch_command','load_service_fraction'})
    switches={k.casefold():k for k in base.initial_switches}
    curt={l.entity.casefold():l.entity for l in base.loads if l.curtailable}
    if set(layout)!=set(switches)|set(curt):raise ClosedLoopContractError('P2_ACTION_MODEL_SET_MISMATCH')
    source=_source(ctx,base.source_bus,set(base.source_vsq))
    f,fmode=_forecast(ctx,h)
    states={}
    faulted={e.switch_entity.casefold() for e in base.branches if e.switch_entity and not e.healthy}
    from opendsssim.controllers.reference.contracts import require_ready
    for k,n in switches.items():
        name,q,e=layout[k]
        if q!='branch_switch_command':raise ClosedLoopContractError('P2_SWITCH_ACTION_QUANTITY_MISMATCH')
        raw=_vector(ctx,name,'branch_open_state')
        if np.any((raw!=0)&(raw!=1)):
            raise ClosedLoopContractError('P2_BAD_NATIVE_SWITCH_READBACK:'+name)
        closed=not bool(np.any(raw))
        if k in faulted:
            # A04 static FaultSpec disables the element; its terminal OPEN readback
            # may still reflect the pre-fault command. Health overrides topology.
            closed=False
        else:require_ready(ctx,name)
        states[n]=closed
    loads=[]; kinds=set()
    for l in base.loads:
        cp=_finite(_ob(ctx,l.entity,'load_available_active_demand_kw'),
                   'P2_MISSING_CURRENT_LOAD_P:'+l.entity,0)
        cq=_finite(_ob(ctx,l.entity,'load_available_reactive_demand_kvar'),
                   'P2_MISSING_CURRENT_LOAD_Q:'+l.entity)
        mult=_series(f,'load.multiplier',l.entity,h)
        fw=_series(f,'load.kw',l.entity,h)
        fq=_series(f,'load.kvar',l.entity,h)
        if fw is not None and fq is not None:
            pseq=fw;qseq=fq;kinds.add('QUALIFIED_ABSOLUTE_PQ')
        elif mult is not None:
            # Reference current nominal P/Q is in the offline case; the
            # public current observation anchors the next-step forecast.
            pseq=tuple(l.p_kw[0]*m for m in mult)
            qseq=tuple(l.q_kvar[0]*m for m in mult)
            kinds.add('QUALIFIED_MULTIPLIER_X_OFFLINE_NOMINAL')
        elif fw is None and fq is None:
            pseq=(cp,)*h;qseq=(cq,)*h;kinds.add('CURRENT_OBSERVATION_PERSISTENCE')
        else:raise ClosedLoopContractError('P2_PARTIAL_ABSOLUTE_PQ_FORECAST:'+l.entity)
        if any(_finite(x,'P2_BAD_FORECAST_LOAD_P',0)>1e7 for x in pseq) or any(not isfinite(x) for x in qseq):
            raise ClosedLoopContractError('P2_BAD_LOAD_FORECAST')
        loads.append(replace(l,p_kw=tuple(pseq),q_kvar=tuple(qseq)))
    out=replace(base,source_vsq={ph:(v,)*h for ph,v in source.items()},
                initial_switches=states,loads=tuple(loads)).validate()
    return out,{'forecast_mode':fmode,'load_forecast_mapping':sorted(kinds),
                'switch_states':'AUTHORIZED_PROBLEMSPEC_OBSERVATION',
                'load_demand':'AUTHORIZED_PROBLEMSPEC_OBSERVATION',
                'thermal':'VOLTAGE_ONLY_EXPLORATORY_UNRATED'}


def _align_results(ctx, values, quantity):
    """Align static AltDSS spelling with real resolved action-layout identities."""
    targets={}
    for item in ctx.action_layout:
        cls,obj,q=item['path']
        if q==quantity:
            k=(cls+'.'+obj)
            if k.casefold() in targets:raise ClosedLoopContractError('DUPLICATE_ACTION_ENTITY')
            targets[k.casefold()]=k
    out={}
    for entity,value in values.items():
        k=entity.casefold()
        if k not in targets:raise ClosedLoopContractError('MODEL_ACTION_ENTITY_NOT_AUTHORIZED:'+entity)
        out[targets[k]]=value
    if len(out)!=len(targets):raise ClosedLoopContractError('MODEL_MISSING_AUTHORIZED_ACTION:'+quantity)
    return out


def p1_action(ctx,result):
    """Collapse shared-bank phases only when physical commands are identical."""
    from .actions import p1_first_step_action
    from opendsssim.controllers.reference.contracts import bound_for
    pv=_align_results(ctx,result.pv_kvar,'pv_reactive_power_command')
    caps=_align_results(ctx,result.cap_states,'capacitor_state')
    taps=_align_results(ctx,result.tap_ratios,'transformer_tap_command')
    collapsed={}
    for entity,states in caps.items():
        entry=bound_for(ctx,entity,'capacitor_state');shape=tuple(entry['shape'])
        count=int(np.prod(shape))
        if len(states)==count:collapsed[entity]=tuple(states)
        elif count==1 and len(states)>1 and len(set(states))==1:
            collapsed[entity]=(int(states[0]),)
        else:raise ClosedLoopContractError('P1_INCOMPATIBLE_CAP_PHASE_DECISION:'+entity)
    adapted=replace(result,pv_kvar=pv,cap_states=collapsed,tap_ratios=taps)
    return p1_first_step_action(ctx,adapted)


def p2_action(ctx,result):
    from .actions import p2_first_step_action
    adapted=replace(result,
        switches=_align_results(ctx,result.switches,'branch_switch_command'),
        load_service=_align_results(ctx,result.load_service,'load_service_fraction'))
    return p2_first_step_action(ctx,adapted)


def step_once(env,base,*,pv_reference_irradiance=None,solve_kwargs=None,allow_apply=False):
    """Single official context -> Gurobi -> ProblemSpec action -> env.step.

    With allow_apply=False, genuinely solve and encode but NEVER change plant.
    No private simulator attributes are read. A failing solver/action aborts.
    """
    h=base.horizon
    ctx=env.controller_context(forecast_horizon=h,required=False,include_static_network=True)
    if isinstance(base,P1Case):
        case,provenance=update_p1(base,ctx,pv_reference_irradiance=pv_reference_irradiance or {})
        from .p1_miqp import solve_p1
        result=solve_p1(case,**(solve_kwargs or {}))
        action=p1_action(ctx,result)
    elif isinstance(base,P2Case):
        case,provenance=update_p2(base,ctx)
        from .p2_milp import solve_p2
        result=solve_p2(case,**(solve_kwargs or {}))
        action=p2_action(ctx,result)
    else:raise ClosedLoopContractError('UNKNOWN_MPC_CASE_TYPE')
    if not env.action_space.contains(action):raise ClosedLoopContractError('ACTION_FAILED_PROBLEMSPEC_GYM_SPACE')
    summary={'episode_id':ctx.episode_id,'decision_index':ctx.completed_steps,
             'decision_time_utc':ctx.decision_time_utc,
             'electrical_sample_time_utc':ctx.electrical_sample_time_utc,
             'action_space_sha256':ctx.action_space_sha256,
             'observation_space_sha256':ctx.observation_space_sha256,
             'forecast_provenance':provenance,
             'solver_status':result.status,'solver_diagnostics':result.diagnostics,
             'action_encoding':'PROBLEMSPEC_A04_ACTIONS_ONLY',
             'prediction_voltage_trajectory':'NOT_EXPORTED_BY_EXISTING_SOLVER',
             'env_step_executed':False}
    if not allow_apply:return summary,action,None
    obs,reward,terminated,truncated,info=env.step(action)
    if not info.get('solution',{}).get('converged'):
        raise ClosedLoopContractError('PLANT_AC_SNAPSHOT_DID_NOT_CONVERGE')
    # Fault-disabled readbacks are expected ONLY for explicit P2 static faults.
    audit=info.get('action_audit',())
    fault_entities=set()
    if isinstance(base,P2Case):
        fault_entities={e.switch_entity.casefold() for e in base.branches
                        if e.switch_entity is not None and not e.healthy}
    bad=[]
    for a in audit:
        status=a.get('status')
        if status=='ADMISSIBLE_APPLIED':continue
        if (status=='FAULT_DISABLED' and isinstance(base,P2Case) and
              str(a.get('native_entity','')).casefold() in fault_entities):
            continue
        bad.append(a)
    if bad:raise ClosedLoopContractError('UNEXPECTED_ACTION_AUDIT_STATUS')
    if isinstance(base,P1Case) and any(a.get('status')!='ADMISSIBLE_APPLIED' for a in audit):
        raise ClosedLoopContractError('P1_ACTION_NOT_APPLIED')
    summary.update({'env_step_executed':True,'reward':reward,
        'terminated':bool(terminated),'truncated':bool(truncated),
        'plant_converged':True,'action_audit':list(audit),
        'post_step_observation_available':bool(obs)})
    return summary,action,(obs,info)
