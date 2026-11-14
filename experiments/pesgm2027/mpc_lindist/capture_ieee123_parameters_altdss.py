#!/usr/bin/env python3
"""Standalone AltDSS-ONLY parameters; never invokes OpenDSSSim Plant/backend.

Loads each pinned IEEE-123 feeder through a NEW isolated AltDSS context, reads
present-time electrical states, and constructs controller-side LinDistFlow
case input data from preexisting A05/A06 snapshots. No optimization is run.
Designed to be launched OUTSIDE the repo with all evidence in Downloads.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
import traceback

VARIANTS=('ieee123_pesgm2027','ieee123_p2_mf01_simple','ieee123_p2_mf02_exotic')

def digest(p:Path)->str:return sha256(p.read_bytes()).hexdigest().upper()

def normalized_name(s)->str:return str(s).casefold()

def pv_injected_kw(pv, full_name):
    """Read *actual solved* PV output (kW), positive for grid injection.

    AltDSS PVSystem does not expose a DSS-object ``kW`` property. The
    inherited CircuitElementMixin.TotalPowers() instead reports complex
    (kW+j*kvar) power ENTERING each terminal; a standard PV has one terminal.
    Negative terminal real power is positive grid injection. Do not fall
    back to Pmpp, Irradiance*kVA, or an invented property if readback fails.
    """
    powers=list(pv.TotalPowers())
    if len(powers)!=1:
        raise RuntimeError('NATIVE_PV_TERMINAL_COUNT_UNSUPPORTED:'+full_name+':'+str(len(powers)))
    try:
        p=complex(powers[0])
    except (TypeError,ValueError,OverflowError) as exc:
        raise RuntimeError('NATIVE_PV_TOTAL_POWER_NOT_COMPLEX:'+full_name) from exc
    if not(math.isfinite(p.real) and math.isfinite(p.imag)):
        raise RuntimeError('NATIVE_PV_TOTAL_POWER_NONFINITE:'+full_name)
    injection_kw=-float(p.real)
    if injection_kw < -1e-6:
        raise RuntimeError('NATIVE_PV_REVERSE_ACTIVE_POWER:'+full_name+':'+str(injection_kw))
    if abs(injection_kw)<=1e-6:
        return 0.0
    return injection_kw

def capture(altdss,repo,variant,native):
    master=repo/'experiments'/'pesgm2027'/'feeders'/variant/'IEEE123Master.dss'
    if digest(master)!=native['master_sha256'].upper():
        raise RuntimeError('NATIVE_MASTER_SOURCE_IDENTITY_MISMATCH:'+variant)
    ctx=altdss.NewContext()
    ctx.Settings.AllowChangeDir=False
    ctx(f'Redirect "{master}"')
    ctx.Solution.Solve()
    if not bool(ctx.Solution.Converged):
        raise RuntimeError('NATIVE_ALTDSS_NOT_CONVERGED:'+variant)
    record={'schema':'MPC_A06R4.altdss_separate_readback.v1',
            'scope':'STATIC_CURRENT_SNAPSHOT_NO_CONTROLLER_ACTIONS',
            'variant':variant,'source_master_sha256':native['master_sha256'],
            'converged':True,'nodes':{},'pv_kw':{},'capacitor_states':{},
            'transformer_taps':{},'switch_closed':{},'network_parameters_from':'ALTDSS_INDEPENDENT_CONTEXT'}
    for bus in ctx.BusNames():
        b=ctx.Bus[bus]
        phases=list(b.Nodes)
        packed=list(b.puVMagAngle)
        if len(packed)!=2*len(phases):raise RuntimeError('NATIVE_BUS_PHASOR_SHAPE:'+str(bus))
        for k,phase in enumerate(phases):
            if int(phase) not in (1,2,3):continue
            kv=float(b.kVBase);vp=float(packed[2*k])
            if not(math.isfinite(kv) and kv>0 and math.isfinite(vp) and vp>=0):
                raise RuntimeError('NATIVE_KVBASE_OR_VPU_INVALID:'+str(bus))
            key=f'{bus}.{int(phase)}'.casefold()
            if key in record['nodes']:raise RuntimeError('DUPLICATE_BUS_PHASE:'+key)
            record['nodes'][key]={'kvbase_ln':kv,'vpu':vp}
    native_objs={o['full_name'].casefold():json.loads(o['properties_json']) for o in native['native_discovery']['objects']}
    for name,p in native_objs.items():
        short=name.split('.',1)[1]
        if name.startswith('line.') and p.get('Switch'):
            record['switch_closed'][name]=not bool(ctx.Line[short].IsOpen(1,0))
        if name.startswith('capacitor.'):
            record['capacitor_states'][name]=[int(x) for x in list(ctx.Capacitor[short].States)]
        if name.startswith('transformer.'):
            record['transformer_taps'][name]=[float(x) for x in list(ctx.Transformer[short].Taps)]
        if name.startswith('pvsystem.'):
            # Solved power entering the (single) PV terminal is negative for
            # real-power generation. Never confuse it with DC Pmpp or AC kVA.
            record['pv_kw'][name]=pv_injected_kw(ctx.PVSystem[short],name)
    expected={s.lower() for s in native['native_discovery']['node_names']}
    if set(record['nodes'])!=expected:
        missing=expected-set(record['nodes']);excess=set(record['nodes'])-expected
        raise RuntimeError(f'NATIVE_NODE_INVENTORY_MISMATCH:{len(missing)}:{len(excess)}')
    return record

def case_to_json(case,notes):
    # Tuple-key maps require explicit per-node rows for safe JSON interchange.
    if hasattr(case,'nodes'):
        obj={'kind':'P1Case','horizon':case.horizon,'nodes':list(case.nodes),
             'sources':[{'bus':n[0],'phase':n[1],'squared_pu':list(seq)} for n,seq in case.sources.items()],
             'branches':[asdict(e) for e in case.branches],
             'loads':[{'bus':n[0],'phase':n[1],'p_kw':list(case.loads_p[n]),'q_kvar':list(case.loads_q[n])}
                      for n in case.nodes],
             'pv':[asdict(p) for p in case.pv],
             'capacitors':[asdict(c) for c in case.capacitors],
             'taps':[asdict(t) for t in case.taps],
             'voltage_band':[case.vmin,case.vmax],
             'weights':{'voltage':case.w_voltage,'switch':case.w_switch,'q':case.w_q,'slack':case.w_slack}}
    else:
        obj={'kind':'P2Case','horizon':case.horizon,'buses':list(case.buses),
             'source_bus':case.source_bus,'source_vsq':{str(k):list(v) for k,v in case.source_vsq.items()},
             'branches':[asdict(e) for e in case.branches],
             'loads':[asdict(ld) for ld in case.loads],
             'initial_switches':dict(case.initial_switches),
             'voltage_only_exploratory':case.voltage_only_exploratory,
             'vmin':case.vmin,'vmax':case.vmax,'dt_hours':case.dt_hours}
    obj['model_assumptions']=notes
    obj['model_to_plant_mismatch_expected']=True
    obj['closed_loop_qualified']=False
    return obj

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo-root',type=Path,required=True)
    ap.add_argument('--baseline-root',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    repo=args.repo_root.resolve(strict=True);baseline=args.baseline_root.resolve(strict=True)
    sys.path.insert(0,str(repo/'src'))
    from opendsssim.controllers.mpc.ieee123_lindist import p1_case,p2_case,case_summary
    from altdss import altdss
    args.output.mkdir(parents=True,exist_ok=False)
    results=[]
    for variant in VARIANTS:
        native=json.loads((baseline/f'{variant}_static_discovery.json').read_text())
        pre=json.loads((baseline/f'{variant}_premodel.json').read_text())
        rt=capture(altdss,repo,variant,native)
        if variant==VARIANTS[0]:case,notes=p1_case(native,pre,rt,horizon=12)
        else:case,notes=p2_case(native,pre,rt,horizon=2)
        case.validate()
        (args.output/f'{variant}_native_parameters.json').write_text(json.dumps(rt,indent=2,allow_nan=False)+'\n',encoding='utf8')
        (args.output/f'{variant}_lindist_case.json').write_text(json.dumps(case_to_json(case,notes),indent=2,allow_nan=False)+'\n',encoding='utf8')
        results.append({'variant':variant,'status':'PASS_CASE_CONTRACT_NOT_NATIVE_CLOSED_LOOP',
                        'summary':case_summary(case,notes),
                        'source_master_sha256':native['master_sha256']})
        print('PASS_A06R4_'+variant.upper()+'_CASE_CONTRACT',flush=True)
    (args.output/'CASE_BUILD_SUMMARY.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf8')
    print('PASS_A06R4_SEPARATE_ALTDSS_CAPTURE_LINDIST_CASES_NO_SOLVER',flush=True)
if __name__=='__main__':main()
