"""Non-mutating A04 implementation-freeze structural/identity gate.

Genuine behavior is separately tested by pytest and predecessor standalone validators.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,os,sys
from pathlib import Path
from datetime import datetime,timezone

EXPECTED_SHA='9261E8F5D83DD3D376D05F62303C80E449B8478206035E6942EC0CC7B46FC268'
EXPECTED_COUNT=188

def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest().upper()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--repo-root',required=True)
    parser.add_argument('--predecessor-manifest',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    repo=Path(args.repo_root).resolve(); manifest=Path(args.predecessor_manifest)
    rows=list(csv.DictReader(manifest.open(encoding='utf-8-sig',newline='')))
    gates={}
    gates['qualified_manifest_sha256']=digest(manifest)==EXPECTED_SHA
    gates['qualified_manifest_rows']=len(rows)==EXPECTED_COUNT
    gates['all_188_predecessor_bytes_preserved']=False
    if gates['qualified_manifest_rows']:
        gates['all_188_predecessor_bytes_preserved']=all(
            (repo/r['RelativePath'].replace('\\','/')).is_file()
            and (repo/r['RelativePath'].replace('\\','/')).stat().st_size==int(r['Bytes'])
            and digest(repo/r['RelativePath'].replace('\\','/'))==r['SHA256'].upper()
            for r in rows)
    ignored={'.git','.pytest_cache','__pycache__'}
    allfiles=[p for p in repo.rglob('*') if p.is_file() and not any(part in ignored for part in p.relative_to(repo).parts) and p.suffix!='.pyc']
    extras={p.relative_to(repo).as_posix() for p in allfiles}-{r['RelativePath'].replace('\\','/') for r in rows}
    allowed={
      'scripts/validation/validate_a04.py',
      'tests/integration/test_a04i4_behavioral_freeze.py',
      'docs/development/patches/OpenDSSSim_A04I4_FullBehavioralQualification_ImplementationFreeze_v01_20261021.md',
    }
    gates['only_three_validation_additions']=extras==allowed and len(allfiles)==191
    gates['a04i3_package_identity_unchanged']=('0.1.0a6' in (repo/'src/opendsssim/__init__.py').read_text())
    result={'status':'PASS' if all(gates.values()) else 'FAIL','gates':gates,'extra_files':sorted(extras),'generated_utc':datetime.now(timezone.utc).isoformat()}
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
    return 0 if result['status']=='PASS' else 1

if __name__=='__main__':sys.exit(main())
