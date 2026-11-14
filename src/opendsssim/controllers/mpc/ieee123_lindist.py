"""A06R4 experimental IEEE-123 LinDistFlow compiler.

Pure controller-side approximation: no AltDSS imports, no simulator or plant handle.
A separate parameter snapshot is REQUIRED for native voltage bases/states.
Static coefficient inputs are from the pinned A05 native inventory and A06R2
premodel. This does not certify AC model fidelity or native action admissibility.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from math import cos, sin, pi, isfinite
from typing import Mapping
import json

VARIANTS=("ieee123_pesgm2027", "ieee123_p2_mf01_simple", "ieee123_p2_mf02_exotic")
FAULTS={"ieee123_p2_mf01_simple":("l45","l77","l93","sw7"),
        "ieee123_p2_mf02_exotic":("l45","l77","l93")}
ANGLE={1:0.0,2:-2*pi/3,3:2*pi/3}

class CompilerError(ValueError):pass

def assert_true(value,tag):
    if not value:raise CompilerError(tag)

def spec(s):
    x=str(s).casefold().split('.')
    return x[0], tuple(int(z) for z in x[1:] if z in ('1','2','3'))

def records(native):
    return {o['full_name'].casefold():json.loads(o['properties_json']) for o in native['objects']}

def runtime_node(runtime,bus,phase):
    name=f'{bus.casefold()}.{phase}'
    try:
        row=runtime['nodes'][name]
        base=float(row['kvbase_ln'])
        pu=float(row['vpu'])
    except (KeyError,TypeError,ValueError) as e:
        raise CompilerError('MISSING_NATIVE_BUS_PHASE_BASE_OR_VOLTAGE:'+name) from e
    assert_true(isfinite(base) and base>0 and isfinite(pu) and pu>=0,'BAD_NATIVE_BUS_PHASE:'+name)
    return base,pu

def bmatrix(name,phases,objs,runtime,kind):
    """Balanced-angle branch approximation; the native matrix is in ohms/unit.

    All power-flow variables are kW and kvar. Squared per-unit voltage drop:
    d(v_phi) = 2*10^-3 * Re[Z_phi,psi exp(j(theta_psi-theta_phi))
                            (P_psi - jQ_psi)] / (kVbase_phi*kVbase_psi).
    """
    p=objs[name.casefold()]
    n=len(phases)
    if kind!='Line':
        # An ideal per-unit transformer is a *declared approximation*, not
        # physically zero impedance. Native AC validation measures the error.
        return tuple(tuple(0. for _ in phases) for _ in phases),tuple(tuple(0. for _ in phases) for _ in phases)
    r=p.get('RMatrix');x=p.get('XMatrix');length=p.get('Length')
    assert_true(str(p.get('Units','')).casefold()=='none','UNSUPPORTED_LINE_LENGTH_UNITS:'+name)
    assert_true(isinstance(r,list) and isinstance(x,list) and len(r)==n and len(x)==n,
                'BAD_NATIVE_R_X_MATRIX:'+name)
    assert_true(all(len(row)==n for row in r+x),'BAD_NATIVE_R_X_SHAPE:'+name)
    length=float(length)
    assert_true(isfinite(length) and length>0,'BAD_LINE_LENGTH:'+name)
    # Native A05 discovery supplies Bus1 and Bus2; the linearized drop is
    # normalized with the sending-side base, not hardcoded 4.16-kV values.
    a=spec(p['Bus1'])[0]
    bases=[runtime_node(runtime,a,ph)[0] for ph in phases]
    rr=[];xx=[]
    for i,ph in enumerate(phases):
        rowr=[];rowx=[]
        for j,pj in enumerate(phases):
            R=float(r[i][j])*length;X=float(x[i][j])*length
            assert_true(isfinite(R) and isfinite(X),'NONFINITE_IMPEDANCE:'+name)
            delta=ANGLE[pj]-ANGLE[ph]
            # 2*1000/(1000*kVphi*1000*kVpsi) = 0.002/(kVphi*kVpsi)
            factor=0.002/(bases[i]*bases[j])
            rowr.append(factor*(R*cos(delta)-X*sin(delta)))
            rowx.append(factor*(X*cos(delta)+R*sin(delta)))
        rr.append(tuple(rowr));xx.append(tuple(rowx))
    return tuple(rr),tuple(xx)

def bus_phase_edges(premodel):
    out=[]
    for e in premodel['branch_phase_orientation']:
        assert_true(e['class'] in ('Line','Transformer'),'UNSUPPORTED_EDGE_CLASS')
        assert_true(len(set(e['phases']))==len(e['phases']),'DUPLICATE_EDGE_PHASE')
        out.append((e['name'],e['class'],e['a'].casefold(),e['b'].casefold(),tuple(e['phases'])))
    return out

def load_phases(props):
    bus,listed=spec(props['Bus1']); count=int(props['Phases']);conn=str(props.get('Conn','wye')).casefold()
    if conn=='delta' and count==1:
        assert_true(len(listed)==2,'DELTA_PAIR_MISSING:'+str(props['Bus1']))
        return bus,listed,(0.5,0.5),'DELTA_PAIR_50_50_PHASE_APPROXIMATION'
    phases=listed or (1,2,3)[:count]
    assert_true(len(phases)==count,'LOAD_PHASE_LAYOUT_MISMATCH:'+str(props['Bus1']))
    return bus,phases,tuple(1/len(phases) for _ in phases),'EQUAL_PHASE_APPROXIMATION'

def inputs(native,premodel,runtime):
    assert_true(runtime['variant']==premodel['variant'],'NATIVE_VARIANT_MISMATCH')
    assert_true(runtime['source_master_sha256']==native['master_sha256'],'NATIVE_MASTER_CHANGED')
    assert_true(bool(runtime['converged']),'NATIVE_SOLUTION_NOT_CONVERGED')
    assert_true(native['feeder']==premodel['variant'],'STATIC_VARIANT_MISMATCH')
    nodes=set(str(n).casefold() for n in native['native_discovery']['node_names'])
    assert_true(nodes==set(runtime['nodes']),'RUNTIME_NATIVE_NODE_SET_MISMATCH')
    assert_true(len(nodes)==premodel['graph']['native_nodes'],'NODE_COUNT_CHANGED')
    return records(native['native_discovery'])

def p1_case(native,premodel,runtime,*,horizon=12):
    from opendsssim.controllers.mpc.contracts import P1Case,P1Branch,P1PV,P1Cap,P1Tap
    assert_true(premodel['variant']==VARIANTS[0],'NOT_P1_VARIANT')
    objs=inputs(native,premodel,runtime)
    assert_true(premodel['graph']['phase_tree'],'P1_PHASE_TREE_NOT_CERTIFIED')
    nodes=tuple(sorted((spec(s)[0],int(s.rsplit('.',1)[1])) for s in native['native_discovery']['node_names']))
    source=premodel['graph']['source_bus'].casefold()
    sources={(source,p):tuple(runtime_node(runtime,source,p)[1]**2 for _ in range(horizon))
             for p in premodel['graph']['source_phases']}
    branches=[]
    for name,kind,a,b,phases in bus_phase_edges(premodel):
        r,x=bmatrix(name,phases,objs,runtime,kind)
        branches.append(P1Branch(name,a,b,phases,r,x))
    lp={n:[0.]*horizon for n in nodes};lq={n:[0.]*horizon for n in nodes};load_notes=[]
    for name,p in objs.items():
        if not name.startswith('load.'):continue
        bus,phases,shares,note=load_phases(p)
        for ph,share in zip(phases,shares):
            n=(bus,ph)
            assert_true(n in lp,'LOAD_AT_UNKNOWN_PHASE:'+name+':'+str(n))
            for t in range(horizon):
                lp[n][t]+=float(p['kW'])*share
                lq[n][t]+=float(p['kvar'])*share
        if 'DELTA' in note:load_notes.append(name)
    pv=[]
    for name,p in objs.items():
        if not name.startswith('pvsystem.'):continue
        bus,phases=spec(p['Bus1']);phases=phases or (1,2,3)[:int(p['Phases'])]
        pv_now=runtime['pv_kw'].get(name)
        assert_true(pv_now is not None,'PV_CURRENT_KW_MISSING:'+name)
        rated=float(p['kVA']);pkw=float(pv_now)
        assert_true(0<=pkw<=rated+1e-7,'PV_CURRENT_EXCEEDS_KVA:'+name)
        pv.append(P1PV(name,tuple((bus,q) for q in phases),tuple(1/len(phases) for _ in phases),
                       rated,tuple(pkw for _ in range(horizon))))
    caps=[];cap_action_notes=[]
    for name,p in objs.items():
        if not name.startswith('capacitor.'):continue
        bus,ph=spec(p['Bus1']);ph=ph or (1,2,3)[:int(p['Phases'])]
        kw=float(sum(p['kvar']))/len(ph)
        states=tuple(int(x) for x in runtime['capacitor_states'][name])
        if len(states)==1 and len(ph)>1:
            cap_action_notes.append(name)
            initial=tuple(states[0] for _ in ph)
        elif len(states)==len(ph):initial=states
        else:raise CompilerError('CAP_STATE_CHANNEL_UNSUPPORTED:'+name)
        caps.append(P1Cap(name,tuple((bus,q) for q in ph),tuple(kw for _ in ph),initial))
    taps=[]
    for name,p in objs.items():
        if not name.startswith('regcontrol.'):continue
        txname=str(p['Transformer'])
        if not txname.casefold().startswith('transformer.'):txname='Transformer.'+txname
        tx=objs[txname.casefold()]
        step=(float(tx['MaxTap'][1])-float(tx['MinTap'][1]))/int(tx['NumTaps'][1])
        cur=float(runtime['transformer_taps'][txname.casefold()][1])
        idx=round((cur-1.0)/step)
        minidx=round((float(tx['MinTap'][1])-1.0)/step)
        maxidx=round((float(tx['MaxTap'][1])-1.0)/step)
        edge=next((x for x in branches if x.name.casefold()==txname.casefold()),None)
        assert_true(edge is not None,'REGULATOR_TRANSFORMER_EDGE_MISSING:'+name)
        # Squared-voltage lift d(v)≈2*step*tap_index. Tap-to-voltage
        # coefficient remains an approximation to be checked against AC.
        affects=tuple((edge.name,ph,2.0*step) for ph in edge.phases)
        taps.append(P1Tap(txname,affects,idx,minidx,maxidx,1.0,step))
    case=P1Case(horizon,nodes,sources,tuple(branches),
                {n:tuple(v) for n,v in lp.items()}, {n:tuple(v) for n,v in lq.items()},
                tuple(pv),tuple(caps),tuple(taps))
    case.validate()
    return case,{'scope':'APPROXIMATE_LINDISTFLOW_NOT_AC_EQUIVALENT',
      'forecast':'PERSISTENCE_OF_CURRENT_NATIVE_PV_AND_DSS_NOMINAL_LOAD',
      'transformer':'IDEAL_PU_BASE_TRANSFER_ZERO_LEAKAGE_APPROXIMATION',
      'regulator':'LINEAR_TAP_LIFT_2_STEP_APPROXIMATION',
      'delta_loads_50_50_phase_allocation':load_notes,
      'shared_capacitor_action_channel_requires_encoder_adapter':cap_action_notes,
      'source_voltage':'CURRENT_NATIVE_VOLTAGE_PU_SQUARED_HELD_FIXED',
      'ready_for_native_closed_loop':False,
      'native_case_contract_valid':True}

def p2_case(native,premodel,runtime,*,horizon=2):
    from opendsssim.controllers.mpc.contracts import P2Case,P2Branch,P2Load
    v=premodel['variant']
    assert_true(v in FAULTS,'NOT_P2_VARIANT')
    objs=inputs(native,premodel,runtime)
    # Merge phase-disjoint regulator transformers sharing the same bus corridor.
    edges=bus_phase_edges(premodel)
    corridors=defaultdict(list)
    for name,kind,a,b,phases in edges:
        if kind=='Transformer' and name.casefold().startswith('transformer.reg'):
            corridors[(a,b)].append((name,kind,a,b,phases))
        else:corridors[(name.casefold(),)].append((name,kind,a,b,phases))
    branches=[];merged=[]
    for group in corridors.values():
        if len(group)==1:entries=group
        else:
            phases=[ph for _,_,_,_,p in group for ph in p]
            assert_true(len(set(phases))==len(phases),'REGULATOR_PARALLEL_OVERLAPPING_PHASES')
            merged.append([g[0] for g in group]);entries=[('Merged.'+'_'.join(g[0].split('.')[-1] for g in group),
                          'Transformer',group[0][2],group[0][3],tuple(sorted(phases)))]
        for name,kind,a,b,phases in entries:
            if name.startswith('Merged.'):r=x=tuple(tuple(0.0 for _ in phases) for _ in phases)
            else:r,x=bmatrix(name,phases,objs,runtime,kind)
            # A05 line.Switch is authoritative switch identification; no invented ratings.
            original=objs.get(name.casefold(),{})
            switch=name if kind=='Line' and bool(original.get('Switch')) else None
            healthy=name.split('.')[-1].casefold() not in FAULTS[v]
            branches.append(P2Branch(name,a,b,phases,r,x,switch,healthy,None))
    loads=[]
    for name,p in objs.items():
        if not name.startswith('load.'):continue
        bus,ph,shares,note=load_phases(p)
        loads.append(P2Load(name,bus,ph,shares,tuple(float(p['kW']) for _ in range(horizon)),
                            tuple(float(p['kvar']) for _ in range(horizon)),1,False))
    allb=tuple(sorted({spec(s)[0] for s in native['native_discovery']['node_names']}))
    source=premodel['graph']['source_bus'].casefold()
    source_vs={ph:tuple(runtime_node(runtime,source,ph)[1]**2 for _ in range(horizon))
               for ph in premodel['graph']['source_phases']}
    switch_states={name:bool(runtime['switch_closed'][name.casefold()])
                   for name in (e.switch_entity for e in branches) if name is not None}
    case=P2Case(horizon,allb,source,source_vs,tuple(branches),tuple(loads),switch_states,
                voltage_only_exploratory=True)
    case.validate()
    return case,{'scope':'VOLTAGE_ONLY_EXPLORATORY_LINDISTFLOW',
       'forecast':'PERSISTENCE_OF_DSS_NOMINAL_LOAD',
       'transformer':'IDEAL_PU_ZERO_LEAKAGE_APPROXIMATION',
       'delta_load':'EQUAL_TERMINAL_PHASE_POWER_ALLOCATION_APPROXIMATION',
       'regulator_corridor_merge':merged,
       'load_priority':'ALL_PRIORITIES=1_EXPLORATORY_NOT_RATIFIED',
       'curtailment':'NO_PARTIAL_LOAD_CURTAILMENT_ASSUMED',
       'initial_switches':'NATIVE_ALTDSS_OPEN_TERMINAL_READBACK',
       'faults':['Line.'+n for n in FAULTS[v]],
       'thermal':'UNRATED_BRANCHES_VOLTAGE_ONLY_NO_THERMAL_SECURITY_CLAIM',
       'ready_for_native_closed_loop':False,
       'native_case_contract_valid':True}

def case_summary(case,notes):
    return {'type':type(case).__name__,'horizon':case.horizon,
            'nodes_or_buses':len(case.nodes) if hasattr(case,'nodes') else len(case.buses),
            'branches':len(case.branches),
            'loads':len(case.loads) if hasattr(case,'loads') else len(case.loads_p),
            'pv':len(case.pv) if hasattr(case,'pv') else 0,
            'capacitors':len(case.capacitors) if hasattr(case,'capacitors') else 0,
            'taps':len(case.taps) if hasattr(case,'taps') else 0,
            'notes':notes}
