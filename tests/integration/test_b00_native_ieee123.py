"""True IEEE123 B00 pilot, including PRE fault health for MF01/MF02."""
from pathlib import Path
import pytest

from experiments.pesgm2027.b00_native_controls.run_b00 import PRIMARY, PRE_FAULTS, run_feeder

REPO = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('feeder', PRIMARY)
def test_b00_native_authority_four_ratified_variants(tmp_path,feeder):
    result = run_feeder(repo_root=REPO, output_root=tmp_path/'run', feeder=feeder,
                        steps=2, load_curve=(.8,1.0), pv_curve=(0,.8),
                        history_level='H1')
    assert result['snapshot_count']==3
    assert result['solves_expected_from_public_boundary']==3
    assert result['action_space_empty']
    assert result['native_controls']=={
        'RegControl':7,'CapControl':0,'InvControl':0,'SwtControl':0}
    assert result['static_disabled_fault_entities']==list(PRE_FAULTS[feeder])
    assert len(result['snapshots'])==3
    for sample in result['snapshots']:
        assert sample['solution']['converged']
        assert sample['solution']['control_iterations'] >= 0
        assert sample['voltages']['bus_phase_voltage_count']>0
        assert sample['transformer_taps']['status']=='NOT_IMPLEMENTED_HISTORY_UNAVAILABLE'
    assert (tmp_path/'run'/feeder/'summary.csv').is_file()
