#!/usr/bin/env python3
"""Independent, read-only P2 MF01/MF02 AltDSS electrical screening.

No authoritative OpenDSSSim plant mutation: every case uses an isolated AltDSS
context; fault/switch Text commands are *qualification fixtures only*.
Do not interpret missing feeder ampacities or provisional tie models as passing
thermal/physical feasibility. Reports are written outside the repository.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
RATIFIED = REPO / 'experiments/pesgm2027/p2_restoration/ratified_design_v01'
VARIANTS = {'MF01': 'ieee123_p2_mf01_simple', 'MF02': 'ieee123_p2_mf02_exotic'}
RUN_CASES = ('MF01_PRE','MF01_RESTORED','MF02_PRE','MF02_SW7_SW8','MF02_A','MF02_B','MF02_C')
SOURCE_HASHES = HERE / 'PINNED_INPUT_SHA256.json'


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def verify_inputs() -> dict:
    expected = json.loads(SOURCE_HASHES.read_text(encoding='utf-8'))
    for rel, digest in expected.items():
        path = REPO / rel
        if not path.is_file():
            raise RuntimeError('PINNED_INPUT_MISSING: ' + rel)
        actual = sha256(path)
        if actual != digest.upper():
            raise RuntimeError(f'PINNED_INPUT_CHANGED: {rel} expected={digest} actual={actual}')
    return expected


def parse_multipliers(value: str) -> list[float]:
    vals = [float(i) for i in value.split(',')]
    if not vals or len(vals) > 24 or any(not math.isfinite(x) or not (0.1 <= x <= 2.0) for x in vals):
        raise ValueError('Load multipliers must be 1-24 finite values in [0.1, 2.0]')
    if len(set(vals)) != len(vals):
        raise ValueError('Duplicate load multipliers are not allowed')
    return vals


def get_names_from_dss(file: Path, cls: str) -> list[str]:
    pat = re.compile(r'^\s*new\s+' + re.escape(cls) + r'\.([A-Za-z0-9_]+)\b', re.I)
    found = []
    for ln in file.read_text(encoding='utf-8-sig').splitlines():
        if ln.lstrip().startswith('!'):
            continue
        m = pat.search(ln)
        if m:
            found.append(m.group(1))
    return found


def collect_names(variant: str) -> tuple[list[str], list[str]]:
    base = REPO / 'experiments/pesgm2027/feeders' / VARIANTS[variant]
    lines = get_names_from_dss(base / 'IEEE123Master.dss', 'Line')
    loads = get_names_from_dss(base / 'IEEE123Loads.DSS', 'Load')
    if len(loads) != 91 or len({n.lower() for n in loads}) != len(loads):
        raise RuntimeError(f'LOAD_DISCOVERY_UNEXPECTED: {variant} {len(loads)}')
    if not all(f'Sw{i}'.lower() in {x.lower() for x in lines} for i in range(1,10 if variant == 'MF01' else 12)):
        raise RuntimeError('SWITCH_DISCOVERY_INCOMPLETE')
    return lines, loads


def explicit_rating_names(variant: str) -> set[str]:
    """Only explicit DSS ampacities count; native default NormAmps does NOT."""
    base = REPO / 'experiments/pesgm2027/feeders' / VARIANTS[variant]
    names = set()
    for path in (base / 'IEEE123Master.dss', base / 'IEEELineCodes.DSS'):
        if re.search(r'\b(?:normamps|emergamps)\s*=', path.read_text(encoding='utf-8-sig'), re.I):
            names.add(str(path.relative_to(REPO)))
    return names


def load_user_ratings(p: Path | None) -> dict[str,float]:
    if p is None:
        return {}
    found = {}
    with p.open(newline='',encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        if not {'line','normal_amps'} <= set(reader.fieldnames or []):
            raise ValueError('Ratings CSV requires line,normal_amps columns')
        for r in reader:
            name = r['line'].strip().lower()
            amps = float(r['normal_amps'])
            if not name or name in found or not math.isfinite(amps) or amps <= 0:
                raise ValueError('Invalid/duplicate rating '+repr(r))
            found[name] = amps
    return found


def bus_voltages(ctx, *, voltage_low: float, voltage_high: float) -> tuple[list[dict],dict,dict]:
    rows, vmap = [], {}
    for name in ctx.BusNames():
        b = ctx.Bus[name]
        nodes = [int(n) for n in b.Nodes]
        packed = list(b.puVMagAngle)
        if len(packed) != 2 * len(nodes):
            raise RuntimeError(f'BUS_VOLTAGE_VECTOR_MISMATCH: {name}')
        base_kv = float(b.kVBase)
        for i, node in enumerate(nodes):
            if node == 0: continue
            pu = float(packed[2*i])
            if not math.isfinite(pu) or pu < 0:
                raise RuntimeError(f'NONFINITE_BUS_PU: {name}.{node}={pu}')
            energized_indicator = (pu >= 0.10)  # voltage heuristic; not source connectivity proof
            status = 'NEAR_ZERO' if not energized_indicator else ('LOW' if pu < voltage_low else ('HIGH' if pu > voltage_high else 'WITHIN_BAND'))
            rows.append({'bus':str(name),'node':node,'phase':('ABC'[node-1] if 1 <= node <= 3 else 'OTHER'),
                         'kvbase_l_n':base_kv,'voltage_pu':pu,'status':status})
            vmap[(str(name).lower(),node)] = pu
    energized = [r for r in rows if r['status'] != 'NEAR_ZERO']
    violations = [r for r in energized if r['status'] in ('LOW','HIGH')]
    stats = {
        'bus_node_phase_count':len(rows),'energized_indicator_count':len(energized),
        'near_zero_voltage_count':len(rows)-len(energized),'violating_phase_count':len(violations),
        'min_energized_pu': min((r['voltage_pu'] for r in energized),default=None),
        'max_energized_pu': max((r['voltage_pu'] for r in energized),default=None),
        'lowest_energized_location':min(energized,key=lambda r:r['voltage_pu'])['bus']+'.'+str(min(energized,key=lambda r:r['voltage_pu'])['node']) if energized else None,
        'highest_energized_location':max(energized,key=lambda r:r['voltage_pu'])['bus']+'.'+str(max(energized,key=lambda r:r['voltage_pu'])['node']) if energized else None,
        'nonpositive_kvbase_count':sum(1 for r in energized if r['kvbase_l_n'] <= 0)
    }
    if len(energized) < 100 or stats['nonpositive_kvbase_count']:
        raise RuntimeError('BAD_VOLTAGE_BASE_OR_EXTENSIVE_ZERO_VOLTAGE: '+repr(stats))
    return rows,vmap,stats


def actual_loads(ctx, names, voltmap, multiplier):
    rows = []
    for name in names:
        ld = ctx.Load[name]
        powers = [complex(p) for p in ld.TotalPowers()]
        if len(powers) != 1: raise RuntimeError(f'UNEXPECTED_LOAD_TERMINALS: {name}={len(powers)}')
        kw = float(powers[0].real)
        if not math.isfinite(kw) or kw < -0.1:
            raise RuntimeError(f'INVALID_ACTUAL_LOAD_POWER {name}: {kw}')
        nodes = [int(x) for x in list(ld.NodeOrder())[:int(ld.NumConductors())] if int(x) in (1,2,3)]
        bus = str(ld.Bus1).split('.')[0].lower()
        if not nodes: raise RuntimeError(f'NO_LOAD_PHASE_NODES {name}')
        pvs = [voltmap.get((bus,n)) for n in nodes]
        if any(p is None for p in pvs): raise RuntimeError(f'MISSING_LOAD_BUS_PHASE {name}: {bus} {nodes}')
        rows.append({'load':name,'bus':bus,'phases':','.join(map(str,nodes)),
                     'nominal_kw':float(ld.kW),'loadmult':multiplier,'actual_kw':kw,
                     'min_terminal_voltage_pu':min(pvs),'all_terminal_voltage_indicator':all(p >= 0.10 for p in pvs)})
    return rows


def actual_lines(ctx, names, ratings):
    rows = []
    for name in names:
        line = ctx.Line[name]
        currents = [complex(x) for x in line.Currents()]
        ncond = int(line.NumConductors()); nt = int(line.NumTerminals())
        node_order = [int(n) for n in line.NodeOrder()]
        if len(currents) != ncond*nt or len(node_order) != len(currents):
            raise RuntimeError(f'BAD_CURRENT_ARRAY {name} cur={len(currents)} nodes={len(node_order)} {ncond}x{nt}')
        rated = ratings.get(name.lower())
        native_rating = float(line.NormAmps)
        for i,(current,node) in enumerate(zip(currents,node_order)):
            if node not in (1,2,3):continue
            amps = float(abs(current))
            if not math.isfinite(amps): raise RuntimeError(f'NONFINITE_CURRENT: {name}')
            rows.append({'line':name,'terminal':i//ncond+1,'phase':'ABC'[node-1],
                         'node':node,'current_a':amps,'native_normamps_a_unverified':native_rating,
                         'qualified_rating_a':rated,'rating_source':'EXTERNAL_CSV' if rated else 'UNKNOWN',
                         'utilization':amps/rated if rated else None,'over_rating':bool(amps > rated) if rated else None})
    return rows


def measure_case(alt, definition, mult, lo, hi, ratings):
    variant=definition['variant']
    master=REPO/'experiments/pesgm2027/feeders'/VARIANTS[variant]/'IEEE123Master.dss'
    lines,loads=collect_names(variant)
    ctx=alt.NewContext()
    ctx.Settings.AllowChangeDir=False
    ctx(f'Redirect "{master}"')
    expected_open=set(range(7,10 if variant == 'MF01' else 11))
    for i in range(1,10 if variant=='MF01' else 12):
        line=ctx.Line[f'Sw{i}']
        if not bool(line.Switch):raise RuntimeError(f'SWITCH_MISSING_DECLARATION: {i}')
        if bool(line.IsOpen(1,0)) != (i in expected_open):
            raise RuntimeError(f'INITIAL_SWITCH_MISMATCH Sw{i}')
    faults={f.lower() for f in definition['faults']}
    for target in definition['faults']:
        ctx(f'Open Line.{target} 1')
    for target in definition['open']:
        ctx(f'Open Line.{target} 1')
    for target in definition['close']:
        if target.lower() in faults:raise RuntimeError('HEALTH_DOWN_RECLOSE_ATTEMPT '+target)
        ctx(f'Close Line.{target} 1')
    for target in definition['faults']:
        if not bool(ctx.Line[target].IsOpen(1,0)):
            raise RuntimeError('FAULT_RECLOSED '+target)
    ctx('Set Mode=SnapShot')
    ctx.Solution.LoadMult=float(mult)
    ctx.Solution.Solve()
    if not bool(ctx.Solution.Converged):
        raise RuntimeError('NATIVE_NOT_CONVERGED')
    volts,vmap,vstats=bus_voltages(ctx,voltage_low=lo,voltage_high=hi)
    lds=actual_loads(ctx,loads,vmap,mult)
    cur=actual_lines(ctx,lines,ratings)
    ranked=sorted(cur,key=lambda r:r['current_a'],reverse=True)
    unrated={r['line'].lower() for r in cur if r['qualified_rating_a'] is None}
    overload=[r for r in cur if r['over_rating']]
    nominal=sum(r['nominal_kw'] for r in lds)
    if abs(nominal-3490)>1e-4: raise RuntimeError(f'NOMINAL_TOTAL_CHANGED {nominal}')
    power=complex(ctx.TotalPower())
    stats={
        'variant':variant,'case':definition['id'],'loadmult':mult,'converged':True,
        'num_buses':int(ctx.NumBuses),'num_nodes':int(ctx.NumNodes),
        'vlow_limit':lo,'vhigh_limit':hi, **vstats,
        'nominal_all_loads_kw':nominal,'nominal_requested_mult_kw':nominal*mult,
        'realized_loads_kw':sum(r['actual_kw'] for r in lds),
        'nonzero_actual_load_count':sum(r['actual_kw']>0.01 for r in lds),
        'terminal_voltage_energized_load_count':sum(r['all_terminal_voltage_indicator'] for r in lds),
        'source_power_kw_signed':float(power.real),'source_power_kvar_signed':float(power.imag),
        'max_line_current_a': ranked[0]['current_a'] if ranked else None,
        'max_line_current_location':ranked[0]['line']+' terminal '+str(ranked[0]['terminal'])+'/'+ranked[0]['phase'] if ranked else None,
        'unrated_line_count':len(unrated), 'rated_line_count':len({r['line'].lower() for r in cur})-len(unrated),
        'over_rating_conductor_count':len(overload),
        'max_known_rating_utilization':max((r['utilization'] for r in cur if r['utilization'] is not None),default=None),
        'voltage_screen':'OUTSIDE_EXPLORATORY_BAND' if vstats['violating_phase_count'] else 'WITHIN_EXPLORATORY_BAND',
        'thermal_screen':'NOT_ASSESSABLE_MISSING_RATINGS' if unrated else ('OVER_KNOWN_RATING' if overload else 'UNDER_SUPPLIED_RATINGS'),
        'physical_tie_feasibility':'NOT_ASSESSABLE_PROVISIONAL_TIE_IMPEDANCE',
        'is_official_experiment':False}
    return stats,volts,lds,cur



def tag_measurement_rows(rows, *, scenario: str, variant: str, case: str, loadmult: float) -> list[dict]:
    """Attach immutable case metadata, allowing an identical in-row load multiplier.

    A load row already carries its multiplier, so duplicate keyword expansion
    must not be used. Reject conflicting source metadata instead of silently
    overwriting it. Build all rows before committing any case to output buffers.
    """
    tags = {'scenario':scenario, 'variant':variant, 'case':case, 'loadmult':loadmult}
    result=[]
    for row in rows:
        for key,value in tags.items():
            if key in row and row[key] != value:
                raise RuntimeError(f'MEASUREMENT_METADATA_CONFLICT: {scenario} {key} {row[key]!r} != {value!r}')
        result.append({**tags, **row})
    return result


def write_csv(path,rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        if rows:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        else: f.write('')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True,help='External evidence directory (not under repo)')
    p.add_argument('--load-mults',default='0.60,0.80,1.00,1.20,1.40')
    p.add_argument('--voltage-low',type=float,default=0.95)
    p.add_argument('--voltage-high',type=float,default=1.05)
    p.add_argument('--ratings-csv',type=Path,default=None,help='Optional engineering-sourced line ampacities, no defaults')
    args=p.parse_args()
    if args.out.resolve()==REPO.resolve() or REPO.resolve() in args.out.resolve().parents:
        raise SystemExit('REFUSE_REPO_WRITES: --out must be outside repository')
    mults=parse_multipliers(args.load_mults)
    if not (0 < args.voltage_low < 1 < args.voltage_high < 2):raise SystemExit('Invalid exploratory pu band')
    pins=verify_inputs()
    ratings=load_user_ratings(args.ratings_csv)
    defs=json.loads((RATIFIED/'P2_RATIFIED_STATIC_CASES_V01.json').read_text(encoding='utf-8'))
    if set(defs)!=set(RUN_CASES)|{'MF02_INVALID'}:raise RuntimeError('RATIFIED_CASE_SET_CHANGED')
    names={k:set(collect_names(k)[0]) for k in VARIANTS}
    if any(x not in {v.lower() for vs in names.values() for v in vs} for x in ratings):
        raise RuntimeError('RATINGS_CSV_HAS_UNKNOWN_LINE')
    for v in VARIANTS:
        if explicit_rating_names(v):
            raise RuntimeError('DSS_EXPLICIT_RATING_DETECTED; REVIEW_MERGE_POLICY_BEFORE_RUN')
    try:from altdss import altdss
    except ImportError as e:raise RuntimeError('altdss required in dedicated runtime environment') from e
    args.out.mkdir(parents=True,exist_ok=True)
    all_summ,all_volts,all_loads,all_lines=[],[],[],[]
    failures=[]
    for case_id in RUN_CASES:
        item=dict(id=case_id,**defs[case_id])
        for m in mults:
            sid=f'{case_id}_LM{m:.2f}'
            try:
                summary,vs,loads,lines=measure_case(altdss,item,m,args.voltage_low,args.voltage_high,ratings)
                if (summary.get('variant'),summary.get('case'),summary.get('loadmult')) != (item['variant'],case_id,m):
                    raise RuntimeError(f'MEASUREMENT_SUMMARY_METADATA_CONFLICT: {sid}')
                # Stage ALL derived rows before committing the case. A failed
                # measurement must never count as completed in the receipt.
                voltage_rows=tag_measurement_rows(vs,scenario=sid,variant=item['variant'],case=case_id,loadmult=m)
                load_rows=tag_measurement_rows(loads,scenario=sid,variant=item['variant'],case=case_id,loadmult=m)
                line_rows=tag_measurement_rows(lines,scenario=sid,variant=item['variant'],case=case_id,loadmult=m)
                all_volts.extend(voltage_rows)
                all_loads.extend(load_rows)
                all_lines.extend(line_rows)
                all_summ.append(summary)
                print('PASS_MEASUREMENT',sid,'vmin=',round(summary['min_energized_pu'],5),'vmax=',round(summary['max_energized_pu'],5),'max_A=',round(summary['max_line_current_a'],3),'thermal=',summary['thermal_screen'],flush=True)
            except Exception as exc:
                failures.append({'scenario':sid,'error':repr(exc)})
                print('FAIL_MEASUREMENT',sid,repr(exc),file=sys.stderr,flush=True)
    for filename,rows in [('STAGE3_SUMMARY.csv',all_summ),('STAGE3_BUS_PHASE_VOLTAGES.csv',all_volts),
                          ('STAGE3_LOAD_REALIZATION.csv',all_loads),('STAGE3_LINE_PHASE_CURRENTS.csv',all_lines)]:
        write_csv(args.out/filename,rows)
    receipt={
        'schema':'opendsssim.p2.stage3.electrical_readonly_screen.v01',
        'source_sha256':pins,'limits_status':'EXPLORATORY_NOT_RATIFIED','voltage_low_pu':args.voltage_low,
        'voltage_high_pu':args.voltage_high,'load_multipliers':mults,'cases':list(RUN_CASES),
        'expected_run_count':len(RUN_CASES)*len(mults),'completed_run_count':len(all_summ),
        'failed_run_count':len(failures),'failures':failures,
        'explicit_ampacity_file':str(args.ratings_csv) if args.ratings_csv else None,
        'explicit_ampacity_sha256':sha256(args.ratings_csv) if args.ratings_csv else None,
        'provisional_tie_models':True,
        'official_controller_source_mutated':False,
        'status':('FAIL_INCOMPLETE_MEASUREMENT' if failures else 'PASS_MEASUREMENTS_ONLY_PENDING_THERMAL_AND_TIE_QUALIFICATION')}
    (args.out/'STAGE3_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    info=[ '# P2 Stage 3 — read-only AltDSS electrical screening', '',
          f"**Receipt:** {receipt['status']}",
          f"**Completed:** {len(all_summ)}/{receipt['expected_run_count']} native snapshot measurements", '',
          'The 0.95–1.05 pu voltage range and synthetic load multipliers are **exploratory**, not final scenario requirements.',
          'All native line currents are measured; **no line ratings are provided in the ratified DSS sources**.',
          'Any external ratings are user-supplied and require independent engineering provenance.',
          'Sw7–Sw10 use provisional short, low-impedance lines; do not assert physical tie/corridor feasibility.',
          'Reported realized load consumption includes voltage-responsive load models and is not equal to an immutable service entitlement.',
          'Near-zero bus voltage is a measurement indicator, NOT a substitute for health/source connectivity proof.',
          'Fault-opening Text commands occur only in private qualifications, never the official controller/plant environment.', '',
          '## Route summary — all demand multipliers', '',
          '| Case | Mult | Min energized pu | Max energized pu | Voltage violations | Peak line A | Rated lines | Status |',
          '|---|---:|---:|---:|---:|---:|---:|---|']
    for s in all_summ:
        info.append(f"| {s['case']} | {s['loadmult']:.2f} | {s['min_energized_pu']:.4f} | {s['max_energized_pu']:.4f} | {s['violating_phase_count']} | {s['max_line_current_a']:.2f} | {s['rated_line_count']} | {s['voltage_screen']} |")
    info+=['','## Open gates','',
           '1. Verify equipment/line ampacities from sourced metadata (not engine defaults).',
           '2. Engineer physically realistic tie lengths, conductor parameters, and switch ratings.',
           '3. Ratify voltage band and actual common load trajectories with time/snapshot semantics.',
           '4. Re-run route screening and compare dynamic feasibility before freezing P2 controller experiment numerics.']
    (args.out/'STAGE3_README.md').write_text('\n'.join(info)+'\n',encoding='utf-8')
    hashes={p.name:sha256(p) for p in sorted(args.out.iterdir()) if p.is_file()}
    (args.out/'STAGE3_OUTPUT_SHA256.json').write_text(json.dumps(hashes,indent=2)+'\n',encoding='utf-8')
    if failures:raise SystemExit(2)
    print('PASS_P2_STAGE3_V01_NATIVE_MEASUREMENTS_ONLY; THERMAL_AND_TIE_FEASIBILITY_UNQUALIFIED')
    print('EVIDENCE_DIR',args.out.resolve())

if __name__=='__main__':main()
