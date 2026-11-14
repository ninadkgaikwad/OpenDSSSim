#!/usr/bin/env python3
"""Preliminary P2 candidate audit; fail closed, no generated files or repo edits."""
from pathlib import Path
import hashlib,json,re

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
repo=Path(__file__).resolve().parents[3] # p2_restoration -> pesgm2027 -> experiments -> repo
base=repo/'experiments/pesgm2027/feeders/ieee123_base'
p2=repo/'experiments/pesgm2027/feeders/ieee123_p2_restoration'
manifest=json.loads((p2/'P2_FEEDER_CANDIDATE.json').read_text())
for name,h in manifest['source_baseline_hashes'].items():
    assert sha(base/name)==h,('source integrity',name)
for name,h in manifest['candidate_hashes'].items():
    assert sha(p2/name)==h,('candidate integrity',name)
master=(p2/'IEEE123Master.dss').read_text(encoding='utf-8-sig')
assert master.lower().count('new line.sw')==8
assert re.search(r'(?im)^New Line.Sw7\s+.*?Bus2=300\s+Switch=Yes',master)
assert re.search(r'(?im)^New Line.Sw8\s+.*?Bus2=94\.1\s+Switch=Yes',master)
for i in range(1,9):
    match=re.search(r'(?im)^New Line\.Sw'+str(i)+r'\s+(.+)$',master)
    assert match,('missing switch line',i)
    body=match.group(1)
    assert body.find('Switch=Yes')>=0 and body.index('Switch=Yes')<body.index('r1=1e-3'),('impedance semantics',i)
    cmd=('Close' if i<=6 else 'Open')+f' Line.Sw{i} 1'
    assert cmd in master,('initial switch state',i)
assert 'PESGM2027_P1_PVSystems' not in master
assert len(re.findall(r'(?im)^\s*New Load\.',(p2/'IEEE123Loads.DSS').read_text()))==91
assert master.count('New Capacitor.')==4
print('PASS_P2_MINIMAL_FEEDER_SOURCE_HASHES_AND_STATIC_DECLARATION_CHECKS')
print('NOTE: source checks only; execute AltDSS native test separately.')
