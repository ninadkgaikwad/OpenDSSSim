#!/usr/bin/env python3
"""INDEPENDENT AltDSS candidate experiments; not an OpenDSSSim controller.

No file mutations inside the feeder directory. Source health is imposed externally
as an already-isolated faulted branch; controller commands are emulated only in
this stand-alone experiment, not through env.step. Never use as official P2 test.
"""
import argparse, csv, json, pathlib, sys

HERE=pathlib.Path(__file__).resolve().parent
FEEDER=HERE.parent/'feeders'/'ieee123_p2_restoration'
SCENARIOS=json.loads((HERE/'P2_SCENARIO_CATALOG.json').read_text())['scenarios']

def test_scenario(alt, case):
    ctx=alt.NewContext()
    ctx.Settings.AllowChangeDir=False
    master=FEEDER/'IEEE123Master.dss'
    ctx(f'Redirect "{master}"')
    # Verify that actual switch initial conductor state was imposed in master.
    initial={f'Sw{i}':bool(ctx.Line[f'Sw{i}'].IsOpen(1,0)) for i in range(1,9)}
    if initial!={f'Sw{i}':i>=7 for i in range(1,9)}:
        raise RuntimeError(f'Invalid switch default states: {initial}')
    if not all(bool(ctx.Line[f'Sw{i}'].Switch) for i in range(1,9)):
        raise RuntimeError('Some switch lines are not declared Switch=Yes')
    # Faulted lines are OPENED by this external pre-isolation fixture, never by an online controller.
    for fault in case['faults']:
        ctx(f'Open Line.{fault} 1')
    for sw in case['close']:
        if sw in case['faults']: raise RuntimeError(f'Attempt to close faulted element {sw}')
        ctx(f'Close Line.{sw} 1')
    for fault in case['faults']:
        if not ctx.Line[fault].IsOpen(1,0):
            raise RuntimeError(f'Faulted element not opened: {fault}')
    for sw in case['close']:
        if ctx.Line[sw].IsOpen(1,0):raise RuntimeError(f'Tie did not close: {sw}')
    ctx.Solution.Solve()
    if not bool(ctx.Solution.Converged):
        raise RuntimeError(f'{case["id"]}: not converged')
    # This is a native-solver smoke test, NOT a voltage and loading feasibility certificate.
    power=complex(ctx.TotalPower())
    return {'scenario':case['id'],'faults':','.join(case['faults']),'ties':','.join(case['close']),
            'converged':bool(ctx.Solution.Converged), 'source_power_kw':round(power.real,6),
            'source_power_kvar':round(power.imag,6),'native_num_buses':int(ctx.NumBuses),
            'native_num_nodes':int(ctx.NumNodes), 'status':'NATIVE_SOLVE_ONLY_NOT_OPERATIONAL_FEASIBILITY'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);args=p.parse_args()
    if not (FEEDER/'IEEE123Master.dss').is_file():raise RuntimeError('Missing feeder master')
    try:from altdss import altdss
    except ImportError as e:raise RuntimeError('altdss not installed in active Python environment') from e
    rows=[]
    static={r['case']:r for r in csv.DictReader((HERE/'P2_STATIC_SCENARIO_SCREEN.csv').open(newline='',encoding='utf-8'))}
    for case in SCENARIOS:
        if static[case['id']]['bus_level_radial'] != 'True':
            # Frozen radiality is hard: never issue a topology known to be cyclic.
            rows.append({'scenario':case['id'],'status':'STRUCTURALLY_REJECTED_BEFORE_ALTDSS',
                         'reason':'candidate is nonradial in bus-level static screen'})
            print('PASS',case['id'],'STRUCTURALLY_REJECTED_BEFORE_ALTDSS')
            continue
        try:r=test_scenario(altdss,case);print(f"PASS {case['id']} {r['status']}");rows.append(r)
        except Exception as e:
            rows.append({'scenario':case['id'],'status':'FAIL','error':f'{type(e).__name__}: {e}'})
            print('FAIL',case['id'],repr(e),file=sys.stderr)
    args.out.mkdir(parents=True,exist_ok=True)
    dst=args.out/'P2_NATIVE_SOLVE_RESULTS.json';dst.write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
    print('EVIDENCE_FILE',dst)
    if any(r['status']=='FAIL' for r in rows):sys.exit(1)
    print('PASS_ALL_NATIVE_SOLVES__NOT_AC_FEASIBILITY_CERTIFICATE')
if __name__=='__main__':main()
