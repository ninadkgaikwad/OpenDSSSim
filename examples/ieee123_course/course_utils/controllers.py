"""Explicit controller-side teaching adapters; the simulator is never patched.

P1 RBC: teach monitor wiring and current-time PV headroom. P2 RBC: S10D
selected-route continuation only; structural preview is NOT an electrical
qualified evaluator. P2 service-first: an optional Gurobi objective-order
sensitivity with unchanged physics and hard constraints.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import io
import json
import sys
import types
from zipfile import ZipFile
import numpy as np
from course_utils.core import INPUT,load_case

S10D_SHA = 'E2B37D6D7EB18E378497B32606F34433BF23B99F7D20AF8FBE4929BF5A14C4F0'
R02_P2_SHA = 'E1196DA89E23DE77127DA71BD993D2F595B2E62C73D82D1FB64C6FBF0131300E'


def p1_rbc_spec(ctx,case):
    """Wire monitor locations explicitly from circuit/captured case metadata.

    This is educational, and is not asserted to reproduce the historical S10C
    P1 RBC protocol exactly. Use the archived scientific data for that study.
    """
    from opendsssim.controllers.reference import P1Monitor,P1Spec
    monitors={}
    devices={e.native_entity.casefold():e for e in ctx.static_network.elements}
    for pv in case.pv:
        monitors[pv.entity]=P1Monitor(bus=str(pv.locations[0][0]))
    for cap in case.capacitors:
        monitors[cap.entity]=P1Monitor(bus=str(cap.locations[0][0]))
    for tap in case.taps:
        e=devices.get(tap.entity.casefold())
        if e is None or not e.terminal_bus_specs:raise RuntimeError('TAP_MONITOR_NOT_IN_NETWORK')
        # The downstream terminal is a declared bus location, NOT a hidden
        # backend read; stripping the phase suffix yields the bus name.
        bus=e.terminal_bus_specs[-1].split('.')[0]
        monitors[tap.entity]=P1Monitor(bus=bus)
    return P1Spec(monitors=monitors,
                  kva={p.entity:p.kva for p in case.pv},
                  tap_step={t.entity:t.step_ratio for t in case.taps},
                  tap_winding_index={t.entity:1 for t in case.taps})


def p2_loads(case):
    from opendsssim.controllers.reference import P2Load
    return tuple(P2Load(ld.entity,ld.bus,ld.priority,ld.curtailable) for ld in case.loads)


def archived_s10d_states(name):
    """Verify and read the original S10D qualified route from its evidence ZIP."""
    route={'ieee123_p2_mf01_simple':'MF01_RATIFIED_PARTIAL',
           'ieee123_p2_mf02_exotic':'MF02_ROUTE_A'}[name]
    p=INPUT/'qualified_routes'/'RBC_S10D_P2_Results_QUALIFIED.zip'
    if hashlib.sha256(p.read_bytes()).hexdigest().upper()!=S10D_SHA:
        raise RuntimeError('ARCHIVED_S10D_ROUTE_EVIDENCE_HASH_DRIFT')
    with ZipFile(p) as z:
        if z.testzip() is not None:raise RuntimeError('S10D_ARCHIVE_CRC_FAILED')
        audits=json.loads(z.read(name+'/live_action_audit_step1.json'))
        preview=json.loads(z.read(name+'/structural_preview.json'))
    if preview.get('status')!='STRUCTURAL_ONLY_NOT_ELECTRICALLY_QUALIFIED':
        raise RuntimeError('S10D_PREVIEW_STATUS_MISMATCH')
    states={}
    for audit in audits:
        entity=audit['native_entity'].casefold()
        state=bool(int(audit['requested_value']))
        if preview['states'][entity]!=state:raise RuntimeError('S10D_PREVIEW_ACTION_MISMATCH')
        if audit['status'] not in ('FAULT_DISABLED','ADMISSIBLE_APPLIED'):
            raise RuntimeError('INVALID_S10D_ACTION')
        if audit['status']=='FAULT_DISABLED' and state:
            raise RuntimeError('S10D_FAULT_SWITCH_NOT_OPEN')
        states[entity]=state
    return route,states,preview


def service_first_solve_function():
    """Load an isolated alternate objective variant without editing a source file.

    This is an EXPLICIT scientific sensitivity. Only two objective priorities
    change. All LinDistFlow equations, fault/connectivity/radiality constraints
    and the original installed P2 solver remain unchanged. Requires Gurobi.
    """
    from opendsssim.controllers.mpc import p2_milp
    path=Path(p2_milp.__file__)
    original=path.read_bytes()
    if hashlib.sha256(original).hexdigest().upper()!=R02_P2_SHA:
        raise RuntimeError('P2_SOLVER_VERSION_NOT_THE_QUALIFIED_R02_RELEASE')
    source=original.decode('utf-8')
    # These are the ONLY two changed expressions; fail if either disappears.
    old1='m.setObjectiveN(op,0,priority=3,'
    old2='m.setObjectiveN(unserved,1,priority=2,'
    if source.count(old1)!=1 or source.count(old2)!=1:
        raise RuntimeError('P2_OBJECTIVE_SOURCE_SHAPE_DRIFT')
    altered=source.replace(old1,'m.setObjectiveN(op,0,priority=2,')
    altered=altered.replace(old2,'m.setObjectiveN(unserved,1,priority=3,')
    module=types.ModuleType('opendsssim.controllers.mpc._educational_service_first')
    module.__package__='opendsssim.controllers.mpc'
    module.__file__=str(path)+'#service_first_in_memory'
    # dataclasses expects its module to exist in sys.modules at class creation.
    sys.modules[module.__name__]=module
    try:exec(compile(altered,module.__file__,'exec'),module.__dict__)
    except BaseException:
        sys.modules.pop(module.__name__,None)
        raise
    return module.solve_p2,{'original_sha256':R02_P2_SHA,
        'model_variant':'SERVICE_FIRST_PRIORITY_SENSITIVITY',
        'model_change':'ONLY_SWAP_UNSERVED_AND_OP_SLACK_GUROBI_PRIORITIES'}


def public_action_audit(audits,faults=()):
    """Fail on healthy-switch mismatches, distinguish FAULT_DISABLED entries."""
    fault={x.casefold() for x in faults}
    healthy=0
    for a in audits:
        st=a['status'];name=a['native_entity'].casefold()
        if st=='FAULT_DISABLED' and name in fault:
            continue
        if st!='ADMISSIBLE_APPLIED':raise RuntimeError('ACTION_NOT_ADMISSIBLE: '+name)
        # Switch realized value is a terminal-open boolean vector. For P1
        # capacitors/readback, different native shapes require distinct audits.
        if name.startswith('line.'):
            requested=a.get('requested_value')
            flags=a.get('realized_value')
            if not isinstance(flags,(list,tuple)) or not flags:
                raise RuntimeError('MISSING_SWITCH_READBACK: '+name)
            actual_closed=not any(bool(x) for x in flags)
            if actual_closed!=bool(requested):
                raise RuntimeError('SWITCH_ACTION_REALIZATION_MISMATCH: '+name)
            healthy+=1
    return healthy
