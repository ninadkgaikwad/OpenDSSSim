#!/usr/bin/env python3
"""Independent offline source, feeder, and bus/phase graph audit for two ratified DESIGN scenarios.
No native solver and no repository mutations. Requires Python stdlib only.
"""
import pathlib,hashlib,json,re,collections,itertools,sys
H=pathlib.Path(__file__).resolve().parent
R=H.parents[3]  # R/experiments/pesgm2027/p2_restoration/ratified_design_v01 -> repo
assert (R/'pyproject.toml').is_file(),f'Expected repository root: {R}'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
PIN=json.loads((H/'SOURCE_PREDECESSOR_SHA256_V01.json').read_text())
BASE=R/'experiments/pesgm2027/feeders/ieee123_p2_restoration'
assert all(sha(BASE/n)==h for n,h in PIN['installed_p2_predecessor'].items()),'P2 predecessor changed'
assert sha(H/'topology_snapshot_qualified_v02.json')==PIN['snapshot_sha256'],'snapshot changed'
assert sha(R/'docs/development/control_science/P2_reconfiguration_restoration/P2_ControlScience_Contract.json')==PIN['science_sha256'],'P2 science contract changed'
S=json.loads((H/'P2_RATIFIED_TWO_SCENARIOS_V01.json').read_text())
C=json.loads((H/'P2_RATIFIED_STATIC_CASES_V01.json').read_text())
original=(BASE/'IEEE123Master.dss').read_bytes()
def dos(s):return (s+'\r\n').encode('utf-8')
old_l78=dos('New Line.L78    Phases=3 Bus1=77.1.2.3   Bus2=78.1.2.3   LineCode=6    Length=0.1')
new_l78=dos('New Line.L78    Phases=3 Bus1=77.1.2.3   Bus2=P2SW11MID.1.2.3   LineCode=6    Length=0.1')
old_sw8=dos('New Line.Sw8    phases=1  Bus1=54.1   Bus2=94.1  Switch=Yes r1=1e-3 r0=1e-3  x1=0.000 x0=0.000 c1=0.000 c0=0.000 Length=0.001')
sw9='New Line.Sw9    phases=3 Bus1=81.1.2.3 Bus2=87.1.2.3 Switch=Yes r1=1e-3 r0=1e-3 x1=0.000 x0=0.000 c1=0.000 c0=0.000 Length=0.001'
sw10='New Line.Sw10   phases=3 Bus1=72.1.2.3 Bus2=89.1.2.3 Switch=Yes r1=1e-3 r0=1e-3 x1=0.000 x0=0.000 c1=0.000 c0=0.000 Length=0.001'
sw11='New Line.Sw11   phases=3 Bus1=P2SW11MID.1.2.3 Bus2=78.1.2.3 Switch=Yes r1=1e-3 r0=1e-3 x1=0.000 x0=0.000 c1=0.000 c0=0.000 Length=0.001'
for variant,dirname in [('MF01','ieee123_p2_mf01_simple'),('MF02','ieee123_p2_mf02_exotic')]:
    feed=R/'experiments/pesgm2027/feeders'/dirname
    assert feed.is_dir(),f'Missing {feed}'
    exp=original
    if variant=='MF02':exp=exp.replace(old_l78,new_l78)
    extra=dos('')+dos('! P2 ratified experiment-design candidate: switch-line equivalents; illustrative low impedance, ratings TBD.')+dos(sw9)
    if variant=='MF02':extra+=dos(sw10)+dos(sw11)
    exp=exp.replace(old_sw8,old_sw8+extra)
    exp=exp.replace(dos('Open Line.Sw8 1'),dos('Open Line.Sw8 1')+dos('Open Line.Sw9 1')+(dos('Open Line.Sw10 1')+dos('Close Line.Sw11 1') if variant=='MF02' else b''))
    assert (feed/'IEEE123Master.dss').read_bytes()==exp,f'Noncanonical {variant} Master.dss'
    for n,h in PIN['installed_p2_predecessor'].items():
      if n!='IEEE123Master.dss':assert sha(feed/n)==h,f'{variant} changed shared source file {n}'
    manifest=json.loads((feed/'P2_FEEDER_VARIANT_MANIFEST_V01.json').read_text())
    assert manifest['switch_count']==(9 if variant=='MF01' else 11)
    for name,h in manifest['source_sha256'].items():assert sha(feed/name)==h,f'{variant} manifest source mismatch {name}'
    print('PASS_REPRODUCIBLE_FEEDER',variant,dirname)
D=json.loads((H/'topology_snapshot_qualified_v02.json').read_text()); loads=[l for n in D['nodes'] for l in n['loads']]
assert len(loads)==91 and len(D['edges'])==134
EXTRAS={'SW9':{'id':'SW9','kind':'switch','a':'81','b':'87','pa':[1,2,3],'pb':[1,2,3]},'SW10':{'id':'SW10','kind':'switch','a':'72','b':'89','pa':[1,2,3],'pb':[1,2,3]}}
# SW11 is a series sectionalizer on L78; L78 remains electrical line, but
# when SW11 is open its 78-side island is disconnected from bus 77.
def graph(faults,closed,variant):
    faults={x.upper() for x in faults};closed={x.upper() for x in closed}
    if faults&closed:raise AssertionError(f'Faulted device closed: {faults&closed}')
    adjacency=collections.defaultdict(list);parent={};links=set();cycles=0
    def find(x):
        if x not in parent:parent[x]=x
        if parent[x]!=x:parent[x]=find(parent[x])
        return parent[x]
    edges=list(D['edges'])+[EXTRAS['SW9']]+([EXTRAS['SW10']] if variant=='MF02' else [])
    for e in edges:
        eid=e['id'].upper()
        if eid in faults:continue
        if e['kind']=='switch' and eid not in closed:continue
        # Original L78 line followed by Sw11: if open, its far side is disconnected;
        # calculate same bus phase connectivity as the physically split circuit.
        if variant=='MF02' and eid=='L78' and 'SW11' not in closed:continue
        for a,b in zip(e['pa'],e['pb']):
            u=f"{e['a']}:{a}";v=f"{e['b']}:{b}"
            adjacency[u].append(v);adjacency[v].append(u)
        key=tuple(sorted((e['a'],e['b'])))
        if key not in links:
            links.add(key);u,v=map(find,key)
            if u==v:cycles+=1
            else:parent[u]=v
    seen={f'{D["source"]}:{p}' for p in (1,2,3)}; q=list(seen)
    for u in q:
        for v in adjacency[u]:
            if v not in seen:seen.add(v);q.append(v)
    ok=[l for l in loads if all(f'{l["bus"]}:{p}' in seen for p in l['need'])]
    return round(sum(l['kw'] for l in ok),2),len(ok),cycles
for id,case in C.items():
    variant=case['variant'];N=9 if variant=='MF01' else 11
    default={f'SW{i}' for i in range(1,7)}|({'SW11'} if variant=='MF02' else set())
    closed=(default|{s.upper() for s in case['close']})-{s.upper() for s in case['open']}
    actual=graph(case['faults'],closed,variant)
    assert actual[:2]==(case['static_connected_kw'],case['static_loads']),(id,actual,case)
    if case.get('expected_structurally_invalid'):
        assert actual[2]>0,(id,actual)
    else:assert actual[2]==0,(id,actual)
    print('PASS_STATIC_CASE',id,actual)
counts=collections.Counter();SWS=[f'SW{i}' for i in range(1,12)]
for mask in range(1<<11):
    closed={name for i,name in enumerate(SWS) if (mask>>i)&1}
    # Exclude actions commanding faults closed; faulted L45/L77/L93 are not switch bits.
    kw,n,cyc=graph(['L45','L77','L93'],closed,'MF02')
    counts['radial' if cyc==0 else 'nonradial']+=1
    if cyc==0 and n==91:counts['full_load']+=1
assert (counts['radial'],counts['nonradial'],counts['full_load'])==(1792,256,6),counts
print('PASS_P2_RATIFIED_MF01_MF02_STATIC_V01; 2048 masks; 1792 radial; 256 cyclic; 6 radial 91-load; NO_NATIVE_POWER_FLOW')
