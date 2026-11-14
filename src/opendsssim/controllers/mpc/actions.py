"""Pure conversion of first-step MPC decisions to the published A04 action space."""
from __future__ import annotations
import numpy as np
from .contracts import MPCInputError
from .p1_miqp import P1MPCResult
from .p2_milp import P2MPCResult


def _encode(ctx, commands):
    from opendsssim.controllers.reference.contracts import encode_action,require_ready
    for entity,quantity in commands:
        # Faulted P2 switches are action channels but may be health-locked;
        # the native decoder decides whether an OPEN command is admissible.
        if quantity != 'branch_switch_command':require_ready(ctx,entity)
    return encode_action(ctx,commands)


def p1_first_step_action(context, result:P1MPCResult):
    if result.status not in ('OPTIMAL','INCUMBENT_NOT_PROVEN_OPTIMAL'):
        raise MPCInputError('P1_NO_SOLVER_INCUMBENT')
    commands={}
    for item in context.action_layout:
        cls,obj,q=item['path'];entity=cls+'.'+obj
        if q=='pv_reactive_power_command':
            if entity not in result.pv_kvar:raise MPCInputError('MISSING_P1_PV_RESULT:'+entity)
            value=float(result.pv_kvar[entity])
        elif q=='capacitor_state':
            if entity not in result.cap_states:raise MPCInputError('MISSING_P1_CAP_RESULT:'+entity)
            value=np.asarray(result.cap_states[entity],dtype=int).reshape(tuple(item['shape']))
        elif q=='transformer_tap_command':
            if entity not in result.tap_ratios:raise MPCInputError('MISSING_P1_TAP_RESULT:'+entity)
            value=float(result.tap_ratios[entity])
        else:raise MPCInputError('UNEXPECTED_P1_CHANNEL:'+q)
        commands[entity,q]=value
    if len(result.pv_kvar)+len(result.cap_states)+len(result.tap_ratios)!=len(commands):
        raise MPCInputError('P1_MODEL_AND_ACTION_CARDINALITY_MISMATCH')
    return _encode(context,commands)


def p2_first_step_action(context,result:P2MPCResult):
    if result.status != 'OPTIMAL':
        raise MPCInputError('P2_REQUIRES_LEXICOGRAPHIC_OPTIMAL_SOLUTION')
    commands={}
    for item in context.action_layout:
        cls,obj,q=item['path'];entity=cls+'.'+obj
        if q=='branch_switch_command':
            if entity not in result.switches:raise MPCInputError('MISSING_P2_SWITCH:'+entity)
            value='CLOSED' if result.switches[entity] else 'OPEN'
        elif q=='load_service_fraction':
            if entity not in result.load_service:raise MPCInputError('MISSING_P2_CURTAILMENT:'+entity)
            value=float(result.load_service[entity])
        else:raise MPCInputError('UNEXPECTED_P2_CHANNEL:'+q)
        commands[entity,q]=value
    if len(result.switches)+len(result.load_service)!=len(commands):
        raise MPCInputError('P2_MODEL_AND_ACTION_CARDINALITY_MISMATCH')
    return _encode(context,commands)
