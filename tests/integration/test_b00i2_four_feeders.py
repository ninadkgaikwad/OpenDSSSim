"""B00I2 native four-feeder qualifier: same A05 authoritative solve path."""
from pathlib import Path
import pytest
from experiments.pesgm2027.b00_native_controls.run_b00 import PRIMARY, PRE_FAULTS, run_feeder
from experiments.pesgm2027.b00_native_controls.b00i2_metrics import analyze
from experiments.pesgm2027.b00_native_controls.render_b00i2 import render
REPO=Path(__file__).resolve().parents[2]

@pytest.mark.parametrize('feeder',PRIMARY)
def test_four_primary_feeders_p0_p1_p2(tmp_path,feeder):
    r=run_feeder(repo_root=REPO,output_root=tmp_path/'native',feeder=feeder,steps=3,
        load_curve=(.75,1.,1.15),pv_curve=(0.,.8,1.),history_level='H2',native_diagnostics=True)
    assert r['snapshot_count']==4
    assert r['static_disabled_fault_entities']==list(PRE_FAULTS[feeder])
    m=analyze(r,3600)
    assert m['p0_status'].startswith('PASS')
    assert m['p1_status'].startswith('PASS')
    assert m['p2_status'].startswith('PASS')
    assert all(x['regcontrols_total']==7 for x in m['rows'])
    assert all(x['queue_pending_post_solve']>=0 for x in m['rows'])
    assert '<svg' in render(m,r)
