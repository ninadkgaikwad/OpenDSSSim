"""Frozen P2 single-source multiphase LinDistFlow restoration MILP.

Actual branch impedance matrices, load phases, health, and optional thermal
ratings are explicit model data, not estimated from native voltage readings.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import pi,cos,sin
from .contracts import P2Case, MPCInputError
from .p1_miqp import MPCSolveError

@dataclass(frozen=True)
class P2MPCResult:
    status:str
    switches:dict[str,bool]
    load_service:dict[str,float]
    predicted_energized_buses:tuple[str,...]
    objectives:dict[str,float]
    diagnostics:dict


def solve_p2(case:P2Case, *, time_limit_s:float=60.,mip_gap:float=0.0,threads:int=1,output_flag:bool=False)->P2MPCResult:
    case.validate()
    if not 0<time_limit_s<=3600 or not 0<=mip_gap<1 or threads<1:raise MPCInputError('BAD_SOLVER_LIMITS')
    try:import gurobipy as gp
    except ImportError as exc:raise MPCSolveError('GUROBIPY_NOT_AVAILABLE') from exc
    GRB=gp.GRB;m=gp.Model('opendsssim_p2_restoration')
    m.Params.OutputFlag=int(output_flag);m.Params.TimeLimit=time_limit_s;m.Params.MIPGap=mip_gap;m.Params.Threads=int(threads)
    H=case.horizon;E=case.branches;N=case.buses;source=case.source_bus
    phases=sorted(set((e.a,p) for e in E for p in e.phases)|set((e.b,p) for e in E for p in e.phases)|
                  set((source,p) for p in case.source_vsq))
    for e in E:
        if e.switch_entity and e.switch_entity not in case.initial_switches:raise MPCInputError('SWITCH_MISSING')
    # Source is a single utility source; add symmetric connectivity flow on
    # each physical corridor. The physical P/Q sign remains a -> b.
    y={};g={};z={};F={};V={};Vhi={};Vlo={};P={};Q={};stherm={};service={};switch_effort={}
    fmax=float(len(N)-1)
    pcap=max(1.,sum(max(x.p_kw) for x in case.loads)*case.flow_multiplier)
    qcap=max(1.,sum(max(abs(q) for q in x.q_kvar) for x in case.loads)*case.flow_multiplier)
    for k in range(H):
        for bus in N:y[bus,k]=m.addVar(vtype=GRB.BINARY,name=f'y[{bus},{k}]')
        m.addConstr(y[source,k]==1)
        # Service variables are defined before phase power-balance constraints.
        for ld in case.loads:
            s=service[ld.entity,k]=m.addVar(lb=0.,ub=1.,name=f'alpha[{ld.entity},{k}]')
            m.addConstr(s<=y[ld.bus,k])
            if not ld.curtailable:m.addConstr(s==y[ld.bus,k])
        for np in phases:
            V[np,k]=m.addVar(lb=0.,ub=2.,name=f'v[{np},{k}]')
            Vhi[np,k]=m.addVar(lb=0.,name=f'vplus[{np},{k}]')
            Vlo[np,k]=m.addVar(lb=0.,name=f'vminus[{np},{k}]')
            if np[0]==source and np[1] in case.source_vsq:
                m.addConstr(V[np,k]==case.source_vsq[np[1]][k])
            else:
                m.addConstr(V[np,k]>=case.vmin**2*y[np[0],k]-Vlo[np,k])
                m.addConstr(V[np,k]<=case.vmax**2*y[np[0],k]+Vhi[np,k])
                # De-energized nodes must not be given fictitious voltage.
                m.addConstr(V[np,k]<=2.*y[np[0],k])
        for e in E:
            a,b=e.a,e.b
            g[e.name,k]=m.addVar(vtype=GRB.BINARY,name=f'g[{e.name},{k}]')
            F[e.name,'ab',k]=m.addVar(lb=0.,ub=fmax,name=f'Fab[{e.name},{k}]')
            F[e.name,'ba',k]=m.addVar(lb=0.,ub=fmax,name=f'Fba[{e.name},{k}]')
            if e.switch_entity:
                z[e.switch_entity,k]=m.addVar(vtype=GRB.BINARY,name=f'z[{e.switch_entity},{k}]')
                if not e.healthy:m.addConstr(z[e.switch_entity,k]==0)
                delta=z[e.switch_entity,k] if e.healthy else 0
                d=switch_effort[e.switch_entity,k]=m.addVar(lb=0.,ub=1.,name=f'switchEffort[{e.switch_entity},{k}]')
                prev=int(case.initial_switches[e.switch_entity]) if k==0 else z[e.switch_entity,k-1]
                m.addConstr(d>=z[e.switch_entity,k]-prev)
                m.addConstr(d>=prev-z[e.switch_entity,k])
            else:delta=1 if e.healthy else 0
            m.addConstr(g[e.name,k]<=delta)
            m.addConstr(g[e.name,k]<=y[a,k]);m.addConstr(g[e.name,k]<=y[b,k])
            m.addConstr(g[e.name,k]>=delta+y[a,k]+y[b,k]-2)
            # Closed healthy physical conductors propagate energization.
            m.addConstr(y[a,k]-y[b,k]<=1-delta)
            m.addConstr(y[b,k]-y[a,k]<=1-delta)
            m.addConstr(F[e.name,'ab',k]<=fmax*g[e.name,k]);m.addConstr(F[e.name,'ba',k]<=fmax*g[e.name,k])
            # Declare *all* phase powers before building coupled voltage drops.
            # The full R/X row below references every phase of this branch;
            # declaring and constraining one phase at a time raises KeyError
            # for a three-phase line (e.g., Line.l10, phase 2, k=0).
            for ph in e.phases:
                P[e.name,ph,k]=m.addVar(lb=-pcap,ub=pcap,name=f'P[{e.name},{ph},{k}]')
                Q[e.name,ph,k]=m.addVar(lb=-qcap,ub=qcap,name=f'Q[{e.name},{ph},{k}]')
            for i,ph in enumerate(e.phases):
                m.addConstr(P[e.name,ph,k]<=pcap*g[e.name,k]);m.addConstr(P[e.name,ph,k]>=-pcap*g[e.name,k])
                m.addConstr(Q[e.name,ph,k]<=qcap*g[e.name,k]);m.addConstr(Q[e.name,ph,k]>=-qcap*g[e.name,k])
                # Voltage drop is only activated on an energized tree edge.
                drop=V[(b,ph),k]-V[(a,ph),k]+gp.quicksum(
                    e.r[i][j]*P[e.name,p,k]+e.x[i][j]*Q[e.name,p,k] for j,p in enumerate(e.phases))
                m.addConstr(drop<=case.voltage_big_m*(1-g[e.name,k]))
                m.addConstr(drop>=-case.voltage_big_m*(1-g[e.name,k]))
                if e.smax_kva is not None:
                    slack=stherm[e.name,ph,k]=m.addVar(lb=0.,name=f'sSlack[{e.name},{ph},{k}]')
                    for facet in range(8):
                        angle=(2*facet+1)*pi/8
                        m.addConstr(cos(angle)*P[e.name,ph,k]+sin(angle)*Q[e.name,ph,k]
                          <=e.smax_kva[i]*cos(pi/8)+slack)
        # Fictitious connectivity flow proves every energized bus has a source path.
        for bus in N:
            incoming=gp.quicksum(F[e.name,'ab',k] if e.b==bus else F[e.name,'ba',k]
                                 for e in E if bus in (e.a,e.b))
            outgoing=gp.quicksum(F[e.name,'ba',k] if e.b==bus else F[e.name,'ab',k]
                                 for e in E if bus in (e.a,e.b))
            if bus!=source:m.addConstr(incoming-outgoing==y[bus,k])
            else:m.addConstr(outgoing-incoming==gp.quicksum(y[b,k] for b in N if b!=source))
        m.addConstr(gp.quicksum(g[e.name,k] for e in E)==gp.quicksum(y[n,k] for n in N)-1)
        # Connected power flow using consistent physical edge directions.
        for n,ph in phases:
            if n==source:continue
            pin=gp.quicksum(P[e.name,ph,k] for e in E if e.b==n and ph in e.phases)
            pout=gp.quicksum(P[e.name,ph,k] for e in E if e.a==n and ph in e.phases)
            qin=gp.quicksum(Q[e.name,ph,k] for e in E if e.b==n and ph in e.phases)
            qout=gp.quicksum(Q[e.name,ph,k] for e in E if e.a==n and ph in e.phases)
            pinj=0;qinj=0
            for ld in case.loads:
                if ld.bus==n and ph in ld.phases:
                    idx=ld.phases.index(ph)
                    pinj=pinj+ld.p_kw[k]*ld.allocation[idx]*service[ld.entity,k]
                    qinj=qinj+ld.q_kvar[k]*ld.allocation[idx]*service[ld.entity,k]
            m.addConstr(pin-pout==pinj);m.addConstr(qin-qout==qinj)
        if case.switch_change_limit is not None:
            m.addConstr(gp.quicksum(switch_effort[e,k] for e in case.initial_switches)<=case.switch_change_limit)
    op=gp.quicksum(Vlo.values())+gp.quicksum(Vhi.values())+gp.quicksum(stherm.values())
    unserved=gp.quicksum(case.dt_hours*ld.priority*ld.p_kw[k]*(1-service[ld.entity,k])
                         for ld in case.loads for k in range(H))
    switching=gp.quicksum(switch_effort.values())
    m.ModelSense=GRB.MINIMIZE
    m.setObjectiveN(op,0,priority=2,weight=1.,abstol=0.,reltol=0.,name='operational_slack')
    m.setObjectiveN(unserved,1,priority=3,weight=1.,abstol=0.,reltol=0.,name='weighted_unserved_energy')
    m.setObjectiveN(switching,2,priority=1,weight=1.,abstol=0.,reltol=0.,name='switching_effort')
    m.optimize()
    if m.Status not in (GRB.OPTIMAL,GRB.TIME_LIMIT,GRB.SUBOPTIMAL) or m.SolCount<1:
        raise MPCSolveError(f'P2_NO_FEASIBLE_INCUMBENT:STATUS={m.Status};SOLCOUNT={m.SolCount}')
    states={s:bool(round(z[s,0].X)) for s in case.initial_switches}
    curt={ld.entity:float(service[ld.entity,0].X) for ld in case.loads if ld.curtailable}
    selected=tuple(sorted(n for n in N if y[n,0].X>0.5))
    opv=sum(v.X for v in Vlo.values())+sum(v.X for v in Vhi.values())+sum(v.X for v in stherm.values())
    unv=sum(case.dt_hours*ld.priority*ld.p_kw[k]*(1-service[ld.entity,k].X) for ld in case.loads for k in range(H))
    swv=sum(v.X for v in switch_effort.values())
    return P2MPCResult('OPTIMAL' if m.Status==GRB.OPTIMAL else 'INCUMBENT_NOT_PROVEN_OPTIMAL',states,curt,selected,
          {'operational_slack':float(opv),'weighted_unserved_kwh':float(unv),'switching_effort':float(swv)},
          {'status_code':int(m.Status),'horizon':H,'thermal_certified':not case.voltage_only_exploratory,
           'bus_level_radiality_only':True,'solver':'gurobipy','forecast_truth_not_exposed':True})
