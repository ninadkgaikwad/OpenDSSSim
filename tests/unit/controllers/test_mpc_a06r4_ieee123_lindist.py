"""A06R4 model-contract tests, not actual AC accuracy or MPC performance."""
import json
import os
from pathlib import Path
import pytest

from opendsssim.controllers.mpc.ieee123_lindist import CompilerError,p1_case,p2_case,case_summary

VARIANTS=('ieee123_pesgm2027','ieee123_p2_mf01_simple','ieee123_p2_mf02_exotic')


def _load(v):
    base=Path(os.environ['MPC_A06R4_BASELINE_ROOT'])
    return (json.loads((base/f'{v}_static_discovery.json').read_text()),
            json.loads((base/f'{v}_premodel.json').read_text()))


def _mock_snapshot(nat):
    """Deliberately synthetic snapshot for DIMENSIONS ONLY; never native proof."""
    d=nat['native_discovery']; obj={o['full_name'].casefold():json.loads(o['properties_json']) for o in d['objects']}
    nodes={}
    for s in d['node_names']:
        bus=s.split('.')[0].casefold()
        nodes[s.casefold()]={'kvbase_ln':0.277128129 if bus=='610' else 2.401777,'vpu':1.0}
    return {'variant':nat['feeder'],'source_master_sha256':nat['master_sha256'],
        'converged':True,'nodes':nodes,
        'pv_kw':{n:float(p.get('kW',0)) for n,p in obj.items() if n.startswith('pvsystem.')},
        'capacitor_states':{n:p['States'] for n,p in obj.items() if n.startswith('capacitor.')},
        'transformer_taps':{n:p['Taps'] for n,p in obj.items() if n.startswith('transformer.')},
        'switch_closed':{n:True for n,p in obj.items() if n.startswith('line.') and p.get('Switch')}}

@pytest.mark.parametrize('variant',VARIANTS)
def test_native_inventory_to_approximate_case_contract(variant):
    native,pre=_load(variant)
    if variant==VARIANTS[0]:
        case,notes=p1_case(native,pre,_mock_snapshot(native))
        assert len(case.nodes)==278 and len(case.branches)==134 and len(case.pv)==10
        assert len(case.capacitors)==4 and len(case.taps)==7
        assert any('CAPACITOR' in k.upper() for k in notes)
    else:
        case,notes=p2_case(native,pre,_mock_snapshot(native))
        assert len(case.buses)>100 and len(case.branches)>120 and len(case.loads)==91
        assert case.voltage_only_exploratory
    case.validate()
    assert not notes['ready_for_native_closed_loop']


def test_missing_native_voltage_base_rejected():
    native,pre=_load(VARIANTS[0]);snap=_mock_snapshot(native)
    snap['nodes'].pop('150.1')
    with pytest.raises(CompilerError,match='RUNTIME_NATIVE_NODE_SET_MISMATCH'):
        p1_case(native,pre,snap)


def test_native_master_drift_rejected():
    native,pre=_load(VARIANTS[0]);snap=_mock_snapshot(native)
    snap['source_master_sha256']='X'*64
    with pytest.raises(CompilerError,match='NATIVE_MASTER_CHANGED'):
        p1_case(native,pre,snap)


def test_p2_thermal_claim_not_silently_added():
    native,pre=_load(VARIANTS[1]);case,notes=p2_case(native,pre,_mock_snapshot(native))
    assert case.voltage_only_exploratory
    assert all(e.smax_kva is None for e in case.branches)
    assert 'NO_THERMAL_SECURITY_CLAIM' in notes['thermal']
