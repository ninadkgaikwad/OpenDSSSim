"""Faithful, read-only display readbacks for the native OpenDSS control queue.

QueueSize is the count of pending actions. Queue is a display/CSV-like list,
not necessarily one string per pending action. Do NOT pop, execute or alter it.
"""
from __future__ import annotations

from numbers import Integral
from typing import Any


def collect_control_queue_snapshot(queue: Any, solution: Any) -> dict[str, Any]:
    """Capture post-solve queue and event log, preserving native representation.

    An empty native queue may render as ["No events"]. A mismatch between raw
    display rows and QueueSize is not evidence of an electrical malfunction.
    Truly contradictory data (nonzero count plus empty-queue sentinel) fails.
    """
    count = queue.QueueSize
    if isinstance(count, bool) or not isinstance(count, Integral) or int(count) < 0:
        raise ValueError("INVALID_NATIVE_QUEUE_ACTION_COUNT")
    count = int(count)
    csv_readback = queue.Queue
    if isinstance(csv_readback, (str, bytes)) or csv_readback is None:
        raise ValueError("INVALID_NATIVE_QUEUE_CSV_REPRESENTATION")
    raw_rows = [str(row) for row in csv_readback]
    event_readback = solution.EventLog
    if isinstance(event_readback, (str, bytes)) or event_readback is None:
        raise ValueError("INVALID_NATIVE_EVENT_LOG_REPRESENTATION")
    events = [str(event) for event in event_readback]
    empty_sentinel = len(raw_rows) == 1 and raw_rows[0].strip().casefold() in ("no events", "no events.")
    if empty_sentinel and count != 0:
        raise ValueError("CONTRADICTORY_NATIVE_QUEUE_EMPTY_SENTINEL")
    if empty_sentinel:
        readback_status = "EMPTY_QUEUE_DISPLAY_SENTINEL"
    elif count == 0 and not raw_rows:
        readback_status = "EMPTY_QUEUE_NO_DISPLAY_ROWS"
    elif len(raw_rows) == count:
        readback_status = "DISPLAY_ROW_COUNT_MATCHES_NOT_ACTION_VERIFIED"
    else:
        readback_status = "DISPLAY_ROW_COUNT_DIFFERS_FROM_ACTION_COUNT"
    return {
        "pending_count": count,
        "pending_csv": raw_rows,            # Exact native display rows, including sentinel
        "raw_csv_row_count": len(raw_rows),
        "readback_status": readback_status,
        "event_log": events,                # Native log, not inferred events
        "interpretation": "POST_SOLVE_DISPLAY_READBACK_NOT_FULL_EVENT_REPLAY",
    }
