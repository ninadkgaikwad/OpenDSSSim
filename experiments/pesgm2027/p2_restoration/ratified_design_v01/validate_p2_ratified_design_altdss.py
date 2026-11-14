#!/usr/bin/env python3
"""Independent AltDSS native solve smoke test, not official controller or voltage/thermal certificate.
No repository writes. Fault commands are standalone pre-isolation fixture, never official env.step.
"""
from pathlib import Path
import argparse, json, sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
VARS={'MF01':'ieee123_p2_mf01_simple','MF02':'ieee123_p2_mf02_exotic'}
def run_one(alt,case):
    variant=case['variant'];n=9 if variant=='MF01' else 11
    master=ROOT/'experiments/pesgm2027/feeders'/VARS[variant]/'IEEE123Master.dss'
    ctx=alt.NewContext();ctx.Settings.AllowChangeDir=False
    ctx(f'Redirect "{master}"')
    # Keep Sw1..6 and Sw11 closed at initial state; Sw7,8,9,10 open.
    for i in range(1,n+1):
        line=ctx.Line[f'Sw{i}']
        assert bool(line.Switch),f'Not declared switch Sw{i}'
        is_open=bool(line.IsOpen(1,0))
        should_be_open=i in ([7,8,9] if variant=='MF01' else [7,8,9,10])
        assert is_open==should_be_open,f'Unexpected initial Sw{i}={is_open}'
    for item in case['faults']:ctx(f'Open Line.{item} 1')
    for item in case['open']:ctx(f'Open Line.{item} 1')
    for item in case['close']:
        if item.lower() in {x.lower() for x in case['faults']}:
            raise RuntimeError('Attempt to close health-down device: '+item)
        ctx(f'Close Line.{item} 1')
    for item in case['faults']:
        if not bool(ctx.Line[item].IsOpen(1,0)):raise RuntimeError('Fault was reclosed: '+item)
    ctx.Solution.Solve()
    if not bool(ctx.Solution.Converged):raise RuntimeError('Native solve not converged')
    # Do not use this alone as AC feasibility; there are no frozen ratings or final test profile.
    return {'case':case['id'],'variant':variant,'converged':True,'num_buses':int(ctx.NumBuses),
       'num_nodes':int(ctx.NumNodes),'status':'NATIVE_SOLVE_ONLY_NOT_OPERATIONALLY_QUALIFIED'}
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);a=parser.parse_args()
    try:from altdss import altdss
    except ImportError as e:raise RuntimeError('altdss required in current environment') from e
    definitions=json.loads((HERE/'P2_RATIFIED_STATIC_CASES_V01.json').read_text())
    results=[];bad=False
    for id,item in definitions.items():
        if item.get('expected_structurally_invalid'):
            results.append({'case':id,'status':'STRUCTURAL_REJECT_BEFORE_NATIVE_SOLVE'})
            continue
        try:
            row=run_one(altdss,dict(id=id,**item));results.append(row);print('PASS',id)
        except Exception as e:
            print('FAIL',id,str(e),file=sys.stderr);results.append({'case':id,'status':'FAIL','error':repr(e)});bad=True
    a.out.mkdir(parents=True,exist_ok=True)
    p=a.out/'P2_RATIFIED_FEEDER_NATIVE_SOLVES_V01.json';p.write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
    print('EVIDENCE',p)
    if bad:sys.exit(1)
    print('PASS_P2_RATIFIED_DESIGN_NATIVE_SMOKE_V01; NOT_AC_FEASIBILITY_CERTIFICATE')
if __name__=='__main__':main()
