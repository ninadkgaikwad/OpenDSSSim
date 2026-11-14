"""Frozen P1 multiphase LinDistFlow, mixed-integer quadratic MPC, Gurobi backend.

Model/data coefficients must be provided through a read-only, explicitly
qualified circuit model. No native simulator, private Plant, or AltDSS access.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import sqrt
from .contracts import P1Case, MPCInputError

class MPCSolveError(RuntimeError):pass

@dataclass(frozen=True)
class P1MPCResult:
    status:str
    objective:float
    gap:float | None
    pv_kvar:dict[str,float]
    cap_states:dict[str,tuple[int,...]]
    tap_ratios:dict[str,float]
    diagnostics:dict


def solve_p1(case:P1Case, *, time_limit_s:float=30., mip_gap:float=0.01, threads:int=1, output_flag:bool=False)->P1MPCResult:
    case.validate()
    if not 0<time_limit_s<=3600 or not 0<=mip_gap<1 or threads<1:raise MPCInputError('BAD_SOLVER_LIMITS')
    # Fail closed on inconsistent phase readback *before* Gurobi is loaded.
    # A shared bank has one physical state. Do not project, vote, or average.
    for cap in case.capacitors:
        if len(set(cap.initial)) != 1:
            raise MPCInputError('P1_SHARED_CAP_BANK_INITIAL_PHASE_DISAGREEMENT:'+cap.entity)
    try:import gurobipy as gp
    except ImportError as exc:raise MPCSolveError('GUROBIPY_NOT_AVAILABLE') from exc
    GRB=gp.GRB
    m=gp.Model('opendsssim_p1_mpc')
    m.Params.OutputFlag=int(output_flag);m.Params.TimeLimit=time_limit_s;m.Params.MIPGap=mip_gap;m.Params.Threads=int(threads)
    h=case.horizon; nodes=case.nodes
    pflow={};qflow={};voltage={};vplus={};vminus={}
    incoming={n:[] for n in nodes}; outgoing={n:[] for n in nodes}
    for e in case.branches:
        for ph in e.phases:
            outgoing[e.parent,ph].append((e.name,ph))
            incoming[e.child,ph].append((e.name,ph))
            for k in range(h):
                pflow[e.name,ph,k]=m.addVar(lb=-GRB.INFINITY,name=f'P[{e.name},{ph},{k}]')
                qflow[e.name,ph,k]=m.addVar(lb=-GRB.INFINITY,name=f'Q[{e.name},{ph},{k}]')
    for n in nodes:
        for k in range(h):
            voltage[n,k]=m.addVar(lb=0.,ub=2.,name=f'v[{n},{k}]')
            if n not in case.sources:
                vplus[n,k]=m.addVar(lb=0.,name=f'vSlackHigh[{n},{k}]')
                vminus[n,k]=m.addVar(lb=0.,name=f'vSlackLow[{n},{k}]')
    qpv={};capacitors={};cchange={};tapidx={};tchange={};tapdelta={}
    for pv in case.pv:
        for k in range(h):
            qmax=sqrt(max(pv.kva**2-pv.available_kw[k]**2,0.))
            qpv[pv.entity,k]=m.addVar(lb=-qmax,ub=qmax,name=f'Qpv[{pv.entity},{k}]')
    # One physical capacitor switching channel is one MPC binary per horizon
    # step, regardless of how many bus phases receive that bank's kvar.
    # These P1Cap entities are native capacitor *banks*, not phase actuators.
    for cap in case.capacitors:
        for k in range(h):
            b=capacitors[cap.entity,k]=m.addVar(
                vtype=GRB.BINARY,name=f'capBank[{cap.entity},{k}]')
            z=cchange[cap.entity,k]=m.addVar(
                lb=0.,ub=1.,name=f'capBankSwitch[{cap.entity},{k}]')
            prev=cap.initial[0] if k==0 else capacitors[cap.entity,k-1]
            m.addConstr(z>=b-prev)
            m.addConstr(z>=prev-b)
    for tap in case.taps:
        for k in range(h):
            t=tapidx[tap.entity,k]=m.addVar(vtype=GRB.INTEGER,lb=tap.min_index,ub=tap.max_index,name=f'tap[{tap.entity},{k}]')
            d=tapdelta[tap.entity,k]=m.addVar(vtype=GRB.INTEGER,lb=-1,ub=1,name=f'tapDelta[{tap.entity},{k}]')
            a=tchange[tap.entity,k]=m.addVar(lb=0.,ub=1.,name=f'tapEffort[{tap.entity},{k}]')
            prev=tap.initial_index if k==0 else tapidx[tap.entity,k-1]
            m.addConstr(t-prev==d);m.addConstr(a>=d);m.addConstr(a>=-d)
    for k in range(h):
        for n in nodes:
            v=voltage[n,k]
            if n in case.sources:m.addConstr(v==case.sources[n][k],name=f'source[{n},{k}]')
            else:
                m.addConstr(v>=case.vmin**2-vminus[n,k])
                m.addConstr(v<=case.vmax**2+vplus[n,k])
                p_dem=case.loads_p.get(n,(0.,)*h)[k]
                q_dem=case.loads_q.get(n,(0.,)*h)[k]
                for pv in case.pv:
                    for pos,node in enumerate(pv.locations):
                        if node==n:
                            p_dem-=pv.available_kw[k]*pv.shares[pos]
                            q_dem=q_dem-qpv[pv.entity,k]*pv.shares[pos]
                for cap in case.capacitors:
                    for j,node in enumerate(cap.locations):
                        if node==n:q_dem=q_dem-cap.kvar[j]*capacitors[cap.entity,k]
                m.addConstr(gp.quicksum(pflow[a,b,k] for a,b in incoming[n])-
                            gp.quicksum(pflow[a,b,k] for a,b in outgoing[n])==p_dem,
                            name=f'Pbal[{n},{k}]')
                m.addConstr(gp.quicksum(qflow[a,b,k] for a,b in incoming[n])-
                            gp.quicksum(qflow[a,b,k] for a,b in outgoing[n])==q_dem,
                            name=f'Qbal[{n},{k}]')
        for e in case.branches:
            for pos,ph in enumerate(e.phases):
                lift=0
                for tap in case.taps:
                    for branch,tph,kappa in tap.affects:
                        if e.name.casefold()==branch.casefold() and ph==tph:
                            lift=lift+kappa*tapidx[tap.entity,k]
                m.addConstr(voltage[(e.child,ph),k]==voltage[(e.parent,ph),k]-
                        gp.quicksum(e.r[pos][j]*pflow[e.name,p,k]+e.x[pos][j]*qflow[e.name,p,k]
                                    for j,p in enumerate(e.phases))+lift,
                        name=f'voltageDrop[{e.name},{ph},{k}]')
    # Convex MIQP: all squared voltage deviation and inverter reactive use;
    # linear penalties on voltage operational slack and switching effort.
    jv=gp.quicksum((voltage[n,k]-1.)*(voltage[n,k]-1.) for n in nodes for k in range(h))
    jq=gp.quicksum(qpv[p.entity,k]*qpv[p.entity,k] for p in case.pv for k in range(h))
    jsw=gp.quicksum(cchange.values())+gp.quicksum(tchange.values())
    js=gp.quicksum(vplus.values())+gp.quicksum(vminus.values())
    m.setObjective(case.w_voltage*jv+case.w_q*jq+case.w_switch*jsw+case.w_slack*js,GRB.MINIMIZE)
    m.optimize()
    status=int(m.Status)
    if status not in (GRB.OPTIMAL,GRB.TIME_LIMIT,GRB.SUBOPTIMAL) or m.SolCount<1:
        raise MPCSolveError(f'P1_NO_FEASIBLE_INCUMBENT:STATUS={status};SOLCOUNT={m.SolCount}')
    k=0
    pv={p.entity:float(qpv[p.entity,k].X) for p in case.pv}
    # Preserve the established phase-ordered result interface. Every phase
    # receives the *same optimized bank decision*; no post-hoc projection.
    caps={c.entity:tuple(int(round(capacitors[c.entity,k].X)) for _ in c.locations)
          for c in case.capacitors}
    taps={t.entity:float(t.nominal_ratio+t.step_ratio*round(tapidx[t.entity,k].X)) for t in case.taps}
    sname='OPTIMAL' if status==GRB.OPTIMAL else 'INCUMBENT_NOT_PROVEN_OPTIMAL'
    return P1MPCResult(sname,float(m.ObjVal),float(m.MIPGap) if m.IsMIP else 0.0,pv,caps,taps,
        {'status_code':status,'horizon':h,'solver':'gurobipy','mode':'MIQP_MULTIPHASE_LINDISTFLOW',
         'capacitor_control_granularity':'ONE_BINARY_PER_PHYSICAL_CAPACITOR_BANK_PER_STEP',
         'capacitor_bank_count':len(case.capacitors),
         'capacitor_phase_injection_count':sum(len(c.locations) for c in case.capacitors),
         'capacitor_bank_binary_variables':len(capacitors),
         'capacitor_bank_switching_auxiliaries':len(cchange),
         'operational_slack_first_step':sum(float(v.X) for (n,k),v in vplus.items() if k==0)+
                                      sum(float(v.X) for (n,k),v in vminus.items() if k==0),
         'assumption':'controller-side linear model; native electrical result is authoritative'})
