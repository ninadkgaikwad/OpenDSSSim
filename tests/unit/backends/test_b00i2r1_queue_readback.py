"""Pure, no-engine tests for native queue display vs pending-action count."""
from types import SimpleNamespace
import pytest

from opendsssim.backends.native_queue_snapshot import collect_control_queue_snapshot


def _read(count, rows, events=()):
    return collect_control_queue_snapshot(
        SimpleNamespace(QueueSize=count, Queue=rows),
        SimpleNamespace(EventLog=list(events)),
    )


def test_native_empty_sentinel_is_not_one_action():
    q=_read(0,['No events'])
    assert q['pending_count']==0 and q['pending_csv']==['No events']
    assert q['raw_csv_row_count']==1
    assert q['readback_status']=='EMPTY_QUEUE_DISPLAY_SENTINEL'


def test_native_zero_actions_empty_display():
    q=_read(0,[])
    assert q['pending_count']==0 and q['raw_csv_row_count']==0
    assert q['readback_status']=='EMPTY_QUEUE_NO_DISPLAY_ROWS'


def test_native_nonempty_queue_keeps_csv_unequal_length():
    q=_read(2,['header','action1','action2'],['event1'])
    assert q['pending_count']==2 and len(q['pending_csv'])==3
    assert q['event_log']==['event1']
    assert q['readback_status']=='DISPLAY_ROW_COUNT_DIFFERS_FROM_ACTION_COUNT'


def test_native_matching_row_count_is_not_certified_as_actions():
    q=_read(1,['action row'])
    assert 'NOT_ACTION_VERIFIED' in q['readback_status']
    assert q['interpretation']=='POST_SOLVE_DISPLAY_READBACK_NOT_FULL_EVENT_REPLAY'


def test_native_nonzero_actions_with_empty_sentinel_fails():
    with pytest.raises(ValueError,match='CONTRADICTORY_NATIVE_QUEUE'):
        _read(1,['No events'])


def test_native_invalid_action_counts_fail_closed():
    for count in (-1,True,1.5):
        with pytest.raises(ValueError,match='INVALID_NATIVE_QUEUE_ACTION_COUNT'):
            _read(count,[])
