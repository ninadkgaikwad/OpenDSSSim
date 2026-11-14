#!/usr/bin/env python3
"""Independent Stage 3 input/source qualification; requires no AltDSS."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location('run_stage3_electrical_screen',HERE/'run_stage3_electrical_screen.py')
mod=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def main():
    pins=mod.verify_inputs()
    defs=json.loads((mod.RATIFIED/'P2_RATIFIED_STATIC_CASES_V01.json').read_text(encoding='utf-8'))
    assert set(defs)==set(mod.RUN_CASES)|{'MF02_INVALID'},'Unexpected case identities'
    assert defs['MF02_INVALID']['expected_structurally_invalid']=='cycle'
    assert mod.parse_multipliers('0.60,0.80,1.00,1.20,1.40')==[.6,.8,1.,1.2,1.4]
    assert mod.load_user_ratings(None)=={}
    for var,line_count,sw_count in [('MF01',127,9),('MF02',129,11)]:
        lines,loads=mod.collect_names(var)
        assert len(lines)==line_count and len(loads)==91,(var,len(lines),len(loads))
        assert len({n.lower() for n in lines})==len(lines)
        assert not mod.explicit_rating_names(var),'New rating source requires review'
        feeder=mod.REPO/'experiments/pesgm2027/feeders'/mod.VARIANTS[var]
        master=(feeder/'IEEE123Master.dss').read_text(encoding='utf-8-sig').lower()
        assert 'r1=1e-3' in master and 'switch=yes' in master,'Pinned source has unexpected tie representation'
        assert 'new line.sw9' in master
        if var=='MF02':
            assert 'new line.sw10' in master and 'new line.sw11' in master
        print('PASS_STAGE3_STATIC',var,'lines',len(lines),'loads',len(loads),'switches',sw_count)
    print('PASS_P2_STAGE3_V01_STATIC_INPUT_QUALIFICATION pinned_files=',len(pins))

if __name__=='__main__':main()
