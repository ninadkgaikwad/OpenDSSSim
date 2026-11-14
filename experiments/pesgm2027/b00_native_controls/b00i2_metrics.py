"""B00I2 P0/P1/P2 recorder aggregation over authoritative result.json only."""
from __future__ import annotations
import csv
import json
import math
from pathlib import Path
from typing import Any

SCHEMA = "B00I2.native_diagnostic_campaign.v01"

class RecorderError(RuntimeError):
    pass

def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise RecorderError(f"INVALID_FINITE_NUMBER: {label}={value!r}")
    return float(value)

def _taps(sample: dict[str, Any]) -> dict[str, tuple[float, ...]] | None:
    reading = sample.get("transformer_taps", {})
    if reading.get("status") != "AVAILABLE":
        return None
    result = {}
    for key, val in reading.get("values", {}).items():
        if not isinstance(val, (list, tuple)):
            val = [val]
        result[str(key).casefold()] = tuple(_number(x, f"tap.{key}") for x in val)
    return result or None

def _cap_states(sample: dict[str, Any]) -> dict[str, Any] | None:
    reading = sample.get("capacitor_states", {})
    if reading.get("status") != "AVAILABLE":
        return None
    return {str(k).casefold(): v for k, v in reading.get("values", {}).items()} or None

def analyze(result: dict[str, Any], dt_seconds: int) -> dict[str, Any]:
    if result.get("schema") != SCHEMA:
        raise RecorderError("B00I2_SCHEMA_MISMATCH")
    snapshots = result.get("snapshots")
    if not isinstance(snapshots, list) or len(snapshots) < 3:
        raise RecorderError("B00I2_EXPECTS_RESET_PLUS_TWO_STEPS")
    if len(snapshots) != result.get("snapshot_count"):
        raise RecorderError("B00I2_SNAPSHOT_COUNT_MISMATCH")
    if dt_seconds <= 0:
        raise RecorderError("INVALID_SAMPLE_INTERVAL")
    rows=[]
    prev_taps=None; prev_caps=None; previous_events=[]
    energy=0.0; tap_proxy=0; cap_proxy=0
    audit=[]
    for idx,s in enumerate(snapshots):
        diag=s.get("native_diagnostics")
        if not isinstance(diag,dict) or diag.get("schema") != "B00I2.native_diagnostics.v01":
            raise RecorderError("MISSING_P0_NATIVE_DIAGNOSTICS")
        sol=diag["solution"]
        if sol["control_mode_name"] != "STATIC" or sol["control_mode_value"] != 0:
            raise RecorderError("B00I2_NOT_STATIC_SNAPSHOT_BASELINE")
        if str(sol["solve_mode"]).casefold() not in ("snapshot", "snapshot", "0") and "snap" not in str(sol["solve_mode"]).casefold():
            raise RecorderError("B00I2_SOLVE_MODE_DRIFT")
        regs=diag["regcontrols"]
        if len(regs)!=7 or len({r["native_entity"].casefold() for r in regs}) != 7:
            raise RecorderError("B00I2_SEVEN_REGCONTROLS_REQUIRED")
        if not all(isinstance(r["enabled"],bool) for r in regs):
            raise RecorderError("REGCONTROL_ENABLED_NOT_READABLE")
        losses=diag["losses"]
        p_loss=_number(losses["p_kw"], "losses.p_kw")
        q_loss=_number(losses["q_kvar"], "losses.q_kvar")
        q=diag["control_queue"]
        if not isinstance(q.get("pending_csv"),list) or not isinstance(q.get("event_log"),list):
            raise RecorderError("CONTROL_QUEUE_NATIVE_READBACK_UNAVAILABLE")
        # QueueSize counts native pending actions; Queue contains CSV/display
        # rows and can be ["No events"] for zero pending actions. Never infer
        # physical operations from its length or formatting.
        count = q.get("pending_count")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise RecorderError("INVALID_QUEUE_PENDING_ACTION_COUNT")
        if "raw_csv_row_count" in q and q["raw_csv_row_count"] != len(q["pending_csv"]):
            raise RecorderError("NATIVE_QUEUE_RAW_ROW_COUNT_INCONSISTENT")
        empty_sentinel = (len(q["pending_csv"]) == 1 and
                          str(q["pending_csv"][0]).strip().casefold() in ("no events", "no events."))
        if empty_sentinel and count != 0:
            raise RecorderError("CONTRADICTORY_NATIVE_QUEUE_EMPTY_SENTINEL")
        readback_status = q.get("readback_status", "LEGACY_UNSPECIFIED")
        events=q["event_log"]
        if previous_events and events[:len(previous_events)]==previous_events:
            new_events=events[len(previous_events):]
            event_trace_status="CUMULATIVE_PREFIX_DELTA"
        elif idx and events:
            new_events=events
            event_trace_status="NEW_ENGINE_LOG_OR_RESET"
        else:
            new_events=events
            event_trace_status="NO_EVENTS_RECORDED" if not events else "INITIAL_LOG"
        previous_events=list(events)
        cur_taps=_taps(s)
        cur_caps=_cap_states(s)
        this_tap=None
        if prev_taps is not None and cur_taps is not None and cur_taps.keys()==prev_taps.keys():
            this_tap=sum(sum(not math.isclose(a,b,rel_tol=0,abs_tol=1e-9) for a,b in zip(cur_taps[k],prev_taps[k]))
                for k in cur_taps if len(cur_taps[k])==len(prev_taps[k]))
            tap_proxy+=this_tap
        this_cap=None
        if prev_caps is not None and cur_caps is not None and cur_caps.keys()==prev_caps.keys():
            this_cap=sum(prev_caps[k]!=cur_caps[k] for k in cur_caps)
            cap_proxy+=this_cap
        prev_taps=cur_taps
        prev_caps=cur_caps
        if idx:energy+=p_loss*dt_seconds/3600.0
        v=s["voltages"]
        row={
            "sample_index":idx,"phase":s["phase"],
            "timestamp_utc":s["time"]["electrical_sample_time_utc"],
            "vmin_nonzero_pu":v["min_nonzero_bus_phase_voltage_pu"],
            "vmax_pu":v["max_all_bus_phase_voltage_pu"],
            "outside_band_nonzero":v["outside_095_105_nonzero_count"],
            "zero_voltage_phases":v["zero_voltage_phase_count"],
            "feeder_p_kw":s["solution"]["total_power_kw"],
            "feeder_q_kvar":s["solution"]["total_power_kvar"],
            "loss_p_kw":p_loss,"loss_q_kvar":q_loss,
            "control_iterations":sol["control_iterations"],
            "control_actions_done":sol["control_actions_done"],
            "regcontrols_enabled":sum(r["enabled"] for r in regs),
            "regcontrols_total":len(regs),
            "tap_net_changes_proxy":this_tap,
            "capacitor_state_changes_proxy":this_cap,
            "queue_pending_post_solve":count,
            "queue_raw_display_rows":len(q["pending_csv"]),
            "queue_readback_status":readback_status,
            "event_log_entries_new":len(new_events),
            "event_trace_status":event_trace_status,
        }
        rows.append(row)
        audit.append({"sample_index":idx,"event_trace_status":event_trace_status,
            "event_log_entries":new_events,"queue_pending_csv":q["pending_csv"],
            "queue_action_count":count,"queue_readback_status":readback_status,
            "regcontrols":regs,"taps":cur_taps,"capacitor_states":cur_caps})
    return {"schema":"B00I2.metrics.v01","feeder":result["feeder"],"rows":rows,
        "audit":audit,"integrated_loss_kwh":energy,"net_tap_change_proxy":tap_proxy,
        "net_capacitor_state_change_proxy":cap_proxy,
        "p0_status":"PASS_OBSERVED_NATIVE_SETTINGS_AND_LOSSES",
        "p1_status":"PASS_ELECTRICAL_SAMPLES_WITH_TAP_AVAILABILITY_DISCLOSED",
        "p2_status":"PASS_READONLY_POST_SOLVE_QUEUE_LOG_NOT_DELAY_VALIDATION",
        "science_caveats":[
            "STATIC Snapshot mode does not reproduce physical regulator delays",
            "net tap position differences are not the number of mechanical tap operations",
            "post-solve control queue may be empty despite actions during solve",
            "native ControlQueue.Queue CSV/display rows are not a count of pending actions",
            "event logs are optional and may not record every control action",
            "P2 PRE topology unserved load is not calculated from zero voltage phases",
        ]}

def write_metrics(metrics:dict[str,Any], output:Path) -> None:
    output.mkdir(parents=True,exist_ok=True)
    (output/'b00i2_metrics.json').write_text(json.dumps(metrics,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    with (output/'b00i2_metrics.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(metrics['rows'][0]));writer.writeheader();writer.writerows(metrics['rows'])


def profiles(steps:int) -> tuple[tuple[float,...],tuple[float,...]]:
    """Deterministic synthetic diagnostic, not utility load/PV data."""
    if steps<3 or steps>576:raise ValueError('B00I2_STEPS_RANGE_3_TO_576')
    load=tuple(round(.84+.23*math.sin(2*math.pi*(i-7)/24),8) for i in range(steps))
    pv=tuple(round(max(0.,math.sin(math.pi*((i%24)-6)/12)),8) for i in range(steps))
    return load,pv
