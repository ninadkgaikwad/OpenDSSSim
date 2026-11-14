"""Pure P0/P1/P2 recorder and offline renderer tests."""
import json
import pytest
from experiments.pesgm2027.b00_native_controls.b00i2_metrics import analyze, RecorderError, write_metrics
from experiments.pesgm2027.b00_native_controls.render_b00i2 import render, render_to_file
from experiments.pesgm2027.b00_native_controls.b00i2_metrics import profiles

def sample(n):
    return {'phase':'reset' if n==0 else 'step',
      'time':{'electrical_sample_time_utc':f'2026-01-01T{n:02}:00:00Z'},
      'solution':{'converged':True,'total_power_kw':100,'total_power_kvar':20},
      'voltages':{'min_nonzero_bus_phase_voltage_pu':0.97,'max_all_bus_phase_voltage_pu':1.04,
                  'outside_095_105_nonzero_count':0,'zero_voltage_phase_count':41},
      'transformer_taps':{'status':'AVAILABLE','values':{'Transformer.T1':[1+n/100]}},
      'capacitor_states':{'status':'AVAILABLE','values':{'Capacitor.C1':[1]}},
      'native_diagnostics':{'schema':'B00I2.native_diagnostics.v01',
        'solution':{'control_mode_name':'STATIC','control_mode_value':0,'solve_mode':'Snap',
                    'control_iterations':2,'control_actions_done':True},
        'regcontrols':[{'native_entity':f'RegControl.R{i}','enabled':True,'settings':{}} for i in range(7)],
        'losses':{'p_kw':5.,'q_kvar':2.},
        'control_queue':{'pending_count':0,'pending_csv':[], 'event_log':['tap R1'] if n else []}}}

def result():
    return {'schema':'B00I2.native_diagnostic_campaign.v01','feeder':'ieee123_p2_mf01_simple',
            'snapshot_count':3,'snapshots':[sample(i) for i in range(3)]}

def test_p0_losses_enabled():
    m=analyze(result(),3600)
    assert m['integrated_loss_kwh']==10 and m['rows'][0]['regcontrols_enabled']==7

def test_p0_reject_mode():
    r=result();r['snapshots'][1]['native_diagnostics']['solution']['control_mode_name']='TIME'
    with pytest.raises(RecorderError,match='NOT_STATIC'):analyze(r,3600)

def test_p0_reject_bad_loss():
    r=result();r['snapshots'][1]['native_diagnostics']['losses']['p_kw']=float('nan')
    with pytest.raises(RecorderError,match='FINITE'):analyze(r,3600)

def test_p0_regulator_count():
    r=result();r['snapshots'][0]['native_diagnostics']['regcontrols'].pop()
    with pytest.raises(RecorderError,match='SEVEN_REGCONTROLS'):analyze(r,3600)

def test_p1_24h():
    a,b=profiles(24)
    assert len(a)==len(b)==24 and all(0.5<=x<=1.2 for x in a) and all(0<=x<=1 for x in b)

def test_p1_tap_proxy():
    m=analyze(result(),3600)
    assert m['net_tap_change_proxy']==2 and m['net_capacitor_state_change_proxy']==0

def test_p2_queue_log():
    m=analyze(result(),3600)
    assert m['rows'][1]['event_log_entries_new']==1
    assert 'POST_SOLVE_QUEUE' in m['p2_status']

def test_p2_queue_empty_sentinel_preserved_as_native_display():
    r=result()
    for s in r['snapshots']:
        s['native_diagnostics']['control_queue'].update(
            pending_count=0, pending_csv=['No events'], raw_csv_row_count=1,
            readback_status='EMPTY_QUEUE_DISPLAY_SENTINEL')
    m=analyze(r,3600)
    assert all(x['queue_pending_post_solve']==0 and x['queue_raw_display_rows']==1 for x in m['rows'])
    assert all(x['queue_readback_status']=='EMPTY_QUEUE_DISPLAY_SENTINEL' for x in m['rows'])
    assert m['audit'][0]['queue_pending_csv']==['No events']


def test_p2_display_rows_not_assumed_to_equal_action_count():
    r=result();q=r['snapshots'][0]['native_diagnostics']['control_queue']
    q.update(pending_count=2,pending_csv=['header','action line'],raw_csv_row_count=2)
    m=analyze(r,3600)
    assert m['rows'][0]['queue_pending_post_solve']==2
    q.update(pending_count=1)
    m=analyze(r,3600)
    assert m['rows'][0]['queue_pending_post_solve']==1
    assert m['rows'][0]['queue_raw_display_rows']==2


def test_p2_queue_contradictory_sentinel_rejected():
    r=result();r['snapshots'][0]['native_diagnostics']['control_queue'].update(
        pending_count=1,pending_csv=['No events'])
    with pytest.raises(RecorderError,match='CONTRADICTORY_NATIVE_QUEUE'):analyze(r,3600)


def test_p2_negative_queue_count_rejected():
    r=result();r['snapshots'][0]['native_diagnostics']['control_queue']['pending_count']=-1
    with pytest.raises(RecorderError,match='INVALID_QUEUE_PENDING'):analyze(r,3600)

def test_renderer_from_recorders(tmp_path):
    r=result();m=analyze(r,3600);write_metrics(m,tmp_path)
    (tmp_path/'result.json').write_text(json.dumps(r))
    render_to_file(tmp_path/'b00i2_metrics.json',tmp_path/'result.json',tmp_path/'plot.html')
    content=(tmp_path/'plot.html').read_text()
    assert '<svg' in content and 'mechanical tap operations' in content

def test_renderer_feeder_contract():
    r=result();m=analyze(r,3600);m['feeder']='OTHER'
    with pytest.raises(RecorderError,match='IDENTITY_MISMATCH'):render(m,r)


# B00I2R2: native boolean semantics must survive JSON-ready serialization.
def test_native_boolean_serialization_preserves_enabled_and_control_actions_done():
    import numpy as np
    from experiments.pesgm2027.b00_native_controls.run_b00 import _plain

    native = {
        'regcontrols': [
            {'native_entity': 'RegControl.R1', 'enabled': True},
            {'native_entity': 'RegControl.R2', 'enabled': False},
            {'native_entity': 'RegControl.R3', 'enabled': np.bool_(True)},
        ],
        'solution': {'control_actions_done': np.bool_(False),
                     'control_iterations': np.int64(2)},
    }
    sample = _plain(native)
    assert [type(r['enabled']) for r in sample['regcontrols']] == [bool, bool, bool]
    assert [r['enabled'] for r in sample['regcontrols']] == [True, False, True]
    assert sample['solution']['control_actions_done'] is False
    assert type(sample['solution']['control_iterations']) is int
    assert [r['enabled'] for r in json.loads(json.dumps(sample))['regcontrols']] == [True, False, True]


def test_native_boolean_serialization_reaches_recorder_and_renderer(tmp_path):
    from experiments.pesgm2027.b00_native_controls.run_b00 import _plain

    source = result()
    for snap in source['snapshots']:
        snap['native_diagnostics']['regcontrols'][0]['enabled'] = False
        snap['native_diagnostics']['solution']['control_actions_done'] = True
    restored = json.loads(json.dumps(_plain(source)))
    assert all(type(s['native_diagnostics']['regcontrols'][0]['enabled']) is bool
               for s in restored['snapshots'])
    assert all(type(s['native_diagnostics']['solution']['control_actions_done']) is bool
               for s in restored['snapshots'])
    metrics = analyze(restored, 3600)
    assert all(row['regcontrols_enabled'] == 6 for row in metrics['rows'])
    assert metrics['p0_status'].startswith('PASS')
    assert metrics['p1_status'].startswith('PASS')
    assert metrics['p2_status'].startswith('PASS')
    assert '<svg' in render(metrics, restored)
    write_metrics(metrics, tmp_path)
    assert (tmp_path / 'b00i2_metrics.json').is_file()
