"""Read-only qualification for installed P2 IEEE-123 Topology Lab snapshot (stdlib)."""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
from collections import defaultdict, deque

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()

def evaluate(d,faults,closed):
    graph=defaultdict(set); parents={}; cycles=0; seen_pairs=set()
    def find(x):
        if x not in parents:parents[x]=x
        if parents[x]!=x:parents[x]=find(parents[x])
        return parents[x]
    for e in d['edges']:
        if e['id'] in faults or (e['kind']=='switch' and e['id'] not in closed):continue
        for pa,pb in zip(e['pa'],e['pb']):
            a=(e['a'],pa);b=(e['b'],pb);graph[a].add(b);graph[b].add(a)
        ab=tuple(sorted((e['a'],e['b'])))
        if ab not in seen_pairs:
            seen_pairs.add(ab)
            ra,rb=find(ab[0]),find(ab[1]);
            if ra==rb:cycles+=1
            else:parents[ra]=rb
    reached={(d['source'],p) for p in (1,2,3) if (d['source'],p) in graph};todo=deque(reached)
    while todo:
        for m in graph[todo.popleft()]:
            if m not in reached:reached.add(m);todo.append(m)
    loads=[l for n in d['nodes'] for l in n['loads']]
    served=[l for l in loads if all((l['bus'],p) in reached for p in l['need'])]
    return len(served),round(sum(l['kw'] for l in served),2),cycles

def main():
    root=Path(__file__).resolve().parent
    feeder=root.parent.parent/'feeders'/'ieee123_p2_restoration'
    # topology_lab is experiments/pesgm2027/p2_restoration/topology_lab
    assert feeder.is_dir(),f'P2 feeder is missing: {feeder}'
    manifest=json.loads((root/'FEEDER_SOURCE_SHA256.json').read_text(encoding='utf8'))
    for name,expected in manifest.items():
        actual=feeder/name
        assert actual.is_file(),f'Missing P2 feeder file: {actual}'
        assert sha(actual)==expected,f'P2 feeder identity drift: {name}'
    data=json.loads((root/'topology_snapshot.json').read_text(encoding='utf8'))
    assert len(data['edges'])==134,(len(data['edges']),'edges')
    assert len(data['nodes'])==130,(len(data['nodes']),'nodes')
    assert len([e for e in data['edges'] if e['kind']=='switch'])==8
    assert sum(len(n['loads']) for n in data['nodes'])==91
    assert sum(l['kw'] for n in data['nodes'] for l in n['loads'])==3490
    for s in data['scenarios']:
        pre=evaluate(data,set(s['faults']),set(['SW1','SW2','SW3','SW4','SW5','SW6']))
        post=evaluate(data,set(s['faults']),set(['SW1','SW2','SW3','SW4','SW5','SW6']+s['close']))
        for label,actual,expected in [('pre',pre,s['pre']),('post',post,s['post'])]:
            assert actual==(expected['connected'],expected['kw'],expected['cycles']),(s['id'],label,actual,expected)
    sys.path.insert(0,str(root))
    from build_offline_html import build
    from tempfile import TemporaryDirectory
    with TemporaryDirectory(prefix='p2lab-') as t:
        target=Path(t)/'index.html';build(root,target)
        assert target.read_bytes()==(root/'index.html').read_bytes(),'index.html not reproducible from snapshot/source'
    print('PASS_P2_TOPOLOGY_LAB_V02: pinned P2 feeder, 134 edges, 8 switches, 91 loads, 7 scenario parities, offline HTML reproducible')
    print('SCOPE=STATIC_TOPOLOGY_ONLY; NO_NATIVE_POWER_FLOW; NO_CONTROLLER; NO_REPO_SOURCE_MUTATION')

if __name__=='__main__':main()
