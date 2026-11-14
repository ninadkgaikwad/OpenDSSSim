"""A04I4A successor source-freeze and genuine AltDSS behavioral qualification."""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from tests.integration.test_a04_switch_authority_amendment import (
    test_live_switching_exclusive_authority_reset_and_preflight,
)
from tests.unit.runtime.test_a04_switch_authority_policy import (
    test_verified_switches_owns_exactly_the_native_switch_controller,
    test_protection_and_monitoring_never_grant_suppression,
    test_hybrid_partition_conflict_fails_closed,
    test_unresolved_switch_target_fails_closed_without_writes,
)

PATCH_ID="OpenDSSSim_A04I4A_SwitchesAuthority_FromDirectedSource_v02_20261022"
CHANGED={
    'src/opendsssim/runtime/binding.py',
    'scripts/validation/validate_a04i3.py',
    'tests/integration/test_a04i3_fault_authority.py',
    'tests/integration/test_a04i4_behavioral_freeze.py',
}
ADDED={
    'tests/unit/runtime/test_a04_switch_authority_policy.py',
    'tests/integration/test_a04_switch_authority_amendment.py',
    'scripts/validation/validate_a04_switch_amendment.py',
    'docs/development/patches/OpenDSSSim_A04I4A_SwitchesAuthority_FromDirectedSource_v02_20261022.md',
}
EXCLUDED={'.git','.pytest_cache','__pycache__'}


def source_files(repo):
    return {f.relative_to(repo).as_posix():f for f in repo.rglob('*')
            if f.is_file() and f.suffix.lower()!='.pyc'
            and not EXCLUDED.intersection(f.relative_to(repo).parts)}


def freeze_gate(repo, manifest):
    with manifest.open('r',encoding='utf-8-sig',newline='') as handle:
        rows=list(csv.DictReader(handle))
    assert len(rows)==191, 'Predecessor manifest must contain 191 files'
    baseline={r['RelativePath'].replace(chr(92),'/'):r for r in rows}
    assert len(baseline)==191, 'Duplicate predecessor manifest paths'
    current=source_files(repo)
    assert set(current)==set(baseline)|ADDED, 'Successor file membership mismatch'
    changed_seen=[]
    for rel,r in baseline.items():
        data=current[rel].read_bytes()
        ident=(len(data),sha256(data).hexdigest().upper())
        expected=(int(r['Bytes']),r['SHA256'].upper())
        if rel in CHANGED:
            assert ident != expected, f'Expected amendment file was unchanged: {rel}'
            changed_seen.append(rel)
        else:
            assert ident == expected, f'Frozen predecessor byte drift: {rel}'
    assert len(changed_seen)==4
    assert len(current)==195
    return {'predecessor_files':191,'frozen_preserved':187,
            'changed':sorted(changed_seen),'added':sorted(ADDED),'qualified_candidate_files':195}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo-root',required=True)
    ap.add_argument('--predecessor-manifest',required=True)
    ap.add_argument('--output',required=True)
    args=ap.parse_args()
    gates={};error=None
    try:
        repo=Path(args.repo_root).resolve()
        result=freeze_gate(repo,Path(args.predecessor_manifest))
        gates['strict_191_to_195_source_freeze']=True
        test_verified_switches_owns_exactly_the_native_switch_controller()
        gates['exact_controller_ownership']=True
        test_protection_and_monitoring_never_grant_suppression()
        gates['monitors_protects_nonowning']=True
        test_hybrid_partition_conflict_fails_closed()
        gates['hybrid_conflict_fail_closed']=True
        test_unresolved_switch_target_fails_closed_without_writes()
        gates['ambiguous_target_fail_closed']=True
        with tempfile.TemporaryDirectory(prefix='a04switchqual_') as tmp:
            path=Path(tmp)
            (path/'external').mkdir()
            (path/'hybrid').mkdir()
            test_live_switching_exclusive_authority_reset_and_preflight(path/'external',False)
            gates['external_live_switch_open_close_reset_preflight']=True
            test_live_switching_exclusive_authority_reset_and_preflight(path/'hybrid',True)
            gates['hybrid_live_switch_open_close_reset_preflight']=True
        status='PASS'
    except Exception as exc:
        status='FAIL';error=f'{type(exc).__name__}: {exc}'
        result={}
    report={'patch_id':PATCH_ID,'status':status,'gates':gates,
            'freeze':result,'error':error,
            'generated_utc':datetime.now(timezone.utc).isoformat()}
    Path(args.output).write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
    return 0 if status=='PASS' else 1

if __name__=='__main__':
    raise SystemExit(main())
