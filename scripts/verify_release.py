#!/usr/bin/env python3
"""Strict SHA256 audit for the GitHub-ready source distribution.

This script needs only Python's standard library. It verifies that original
qualified core source and every added educational file have not changed.
It intentionally ignores transient Python caches and generated output runs.
"""
from pathlib import Path
from hashlib import sha256
import csv,json,sys
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'RELEASE_MANIFEST_SHA256.csv'
IGNORE_DIRS={'.git','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','.venv','venv','build','dist'}
IGNORE_PARTS={'Thumbs.db','.DS_Store'}

def included(p):
    rel=p.relative_to(ROOT)
    if any(x in IGNORE_DIRS for x in rel.parts):return False
    if p.name in IGNORE_PARTS or p.suffix in ('.pyc','.pyo'):return False
    if str(rel).startswith('examples/ieee123_course/output/'):
        tail=rel.parts[3:]
        return not tail or tail[0] in ('README.md','.gitkeep','sample_offline')
    return True

def main():
    with MANIFEST.open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
    expected={row['relative_path']:(int(row['bytes']),row['sha256'].upper()) for row in rows}
    actual={p.relative_to(ROOT).as_posix():p for p in ROOT.rglob('*') if p.is_file() and included(p) and p!=MANIFEST}
    if set(expected)!=set(actual):
        print('FILE_SET_MISMATCH',sorted(set(expected)^set(actual))[:25]);return 2
    for rel,p in actual.items():
        b=p.read_bytes()
        if len(b)!=expected[rel][0] or sha256(b).hexdigest().upper()!=expected[rel][1]:
            print('FILE_HASH_MISMATCH',rel);return 3
    source=json.loads((ROOT/'docs/release/RELEASE_SOURCE_PRESERVATION.json').read_text())
    if source['byte_identical_to_qualified_source']!=509 or source['protected_executable_source_changed']:
        print('SOURCE_PROVENANCE_INVALID');return 4
    print('RELEASE_SHA256=PASS; FILES='+str(len(expected))+'; ORIGINAL_QUALIFIED_SOURCE_UNCHANGED=509/510; README_ONLY_CHANGE=YES')
    return 0
if __name__=='__main__':sys.exit(main())
