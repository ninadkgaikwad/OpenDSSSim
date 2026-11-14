"""Authorized A04 problem contracts and A05 detached action encoding.

Neither a controller nor this adapter obtains a Plant/backend/native handle.
Only public ControllerContext fields are used by the controllers.
"""
from __future__ import annotations
import math
from typing import Any, Mapping
import numpy as np

class ControllerContractError(ValueError):
    pass

def _g(name: str, registry, quantity: str, entity: str | None = None):
    from opendsssim.problem import SelectionGroup, SemanticQuery
    return SelectionGroup(name, (SemanticQuery(registry, quantity=quantity, native_entity=entity),))

def make_p1_problem(*, pv: tuple[str, ...], capacitors: tuple[str, ...], transformers: tuple[str, ...]):
    """External P1 authority over exactly configured devices; A04 suppresses native RegControls."""
    from opendsssim.problem import (ProblemSpec, ActionSpec, ObservationSpec, SelectionGroup,
        RegistryKind, ControlAuthorityMode, ControlAuthoritySpec, ActionRestriction, SemanticQuery)
    if not pv or not capacitors or not transformers:
        raise ControllerContractError('P1 requires explicit nonempty device groups')
    channels = [(e, 'pv_reactive_power_command') for e in pv] + [
        (e, 'capacitor_state') for e in capacitors] + [
        (e, 'transformer_tap_command') for e in transformers]
    entities = tuple(e for e, _ in channels)
    if len({e.casefold() for e in entities}) != len(entities):
        raise ControllerContractError('P1 duplicate action entity')
    return ProblemSpec.create('rbc-p1-voltage', 's09a-v1',
        observations=ObservationSpec(groups=(_g('voltage', RegistryKind.STATE, 'bus_voltage_pu'),
                _g('caps', RegistryKind.STATE, 'capacitor_state'),
                _g('taps', RegistryKind.STATE, 'transformer_tap_position'),
                _g('converged', RegistryKind.STATE, 'solution_converged'))),
        actions=ActionSpec(groups=tuple(
            SelectionGroup('a'+str(i), (SemanticQuery(RegistryKind.ACTION, quantity=q, native_entity=e),),
                action_restriction=ActionRestriction(allowed_values=(0,1)) if q=='capacitor_state' else None)
            for i,(e,q) in enumerate(channels))),
        control_authority=ControlAuthoritySpec(ControlAuthorityMode.EXTERNAL,external_entities=entities))

def make_p2_problem(*, switches: tuple[str,...], curtailable_loads: tuple[str,...], faulted: tuple[str,...]):
    """Health is A04 FaultSpec, commands are only selected switch/load-service channels."""
    from opendsssim.problem import (ProblemSpec, ActionSpec, ObservationSpec, RegistryKind,
        ControlAuthorityMode, ControlAuthoritySpec, FaultSpec, DeviceRef)
    if not switches or not faulted:
        raise ControllerContractError('P2 requires switches and explicit health-down elements')
    all_actions = [(e, 'branch_switch_command') for e in switches] + [
        (e, 'load_service_fraction') for e in curtailable_loads]
    entities=tuple(e for e,q in all_actions)
    if len({x.casefold() for x in entities}) != len(entities):
        raise ControllerContractError('P2 duplicate action entity')
    return ProblemSpec.create('rbc-p2-graph-restoration', 's09a-v1',
        observations=ObservationSpec(groups=(
            _g('switch_states', RegistryKind.STATE,'branch_open_state'),
            _g('load_p', RegistryKind.STATE,'load_available_active_demand_kw'),
            _g('load_q', RegistryKind.STATE,'load_available_reactive_demand_kvar'),
            _g('bus_voltages', RegistryKind.STATE,'bus_voltage_pu'),
            _g('converged', RegistryKind.STATE,'solution_converged'))),
        actions=ActionSpec(groups=tuple(_g('a'+str(i),RegistryKind.ACTION,q,e) for i,(e,q) in enumerate(all_actions))),
        faults=(FaultSpec('fixed-health', tuple(DeviceRef(x) for x in faulted)),),
        control_authority=ControlAuthoritySpec(ControlAuthorityMode.EXTERNAL,external_entities=entities))

def _scalar_action(layout: Mapping[str,Any], value: Any):
    st=layout['space_type']; shape=tuple(layout.get('shape',()))
    if st=='Box':
        arr=np.asarray(value,dtype=np.float64)
        if arr.shape!=shape or not np.all(np.isfinite(arr)):
            raise ControllerContractError(f'Nonfinite or incompatible Box action {layout["path"]}: {arr.shape} expected {shape}')
        low=layout.get('low');high=layout.get('high')
        if (low is not None and np.any(arr<low-1e-10)) or (high is not None and np.any(arr>high+1e-10)):
            raise ControllerContractError(f'Action outside bounds {layout["path"]}')
        return arr
    if st=='Discrete':
        domain=tuple(layout.get('domain_values',()))
        if isinstance(value,str):
            if value not in domain:raise ControllerContractError('Unknown enum requested')
            return int(domain.index(value))
        val=int(value)
        if val<0 or (domain and val>=len(domain)):
            raise ControllerContractError('Categorical index out of range')
        return val
    if st in {'MultiDiscrete','MultiBinary'}:
        arr=np.asarray(value,dtype=np.int64)
        if arr.shape!=shape:raise ControllerContractError('Incompatible discrete array shape')
        if st=='MultiBinary' and np.any((arr!=0)&(arr!=1)):raise ControllerContractError('Not binary')
        return arr
    raise ControllerContractError(f'Unsupported Gym type {st}')

def encode_action(context: Any, commands: Mapping[tuple[str,str],Any]):
    """Complete action vector from current authorized layout, never direct native actions.

    Key: (case-insensitive native entity, exact semantic quantity). Refuse missing,
    extra or duplicate channels instead of filling them with invented defaults.
    """
    layout=tuple(context.action_layout)
    if len(commands)!=len(layout):
        raise ControllerContractError(f'Incomplete action: {len(commands)} supplied vs {len(layout)} declared')
    normalized={}
    for (entity,quantity),value in commands.items():
        key=(entity.casefold(),quantity)
        if key in normalized:raise ControllerContractError('Duplicate command')
        normalized[key]=value
    frame={}
    for entry in layout:
        path=tuple(entry['path'])
        if len(path)!=3:raise ControllerContractError('Unexpected native action path')
        key=((path[0]+'.'+path[1]).casefold(),path[2])
        if key not in normalized:raise ControllerContractError('Missing action '+repr(key))
        node=frame.setdefault(path[0],{}).setdefault(path[1],{})
        if path[2] in node:raise ControllerContractError('Duplicate compiled action path')
        node[path[2]]=_scalar_action(entry,normalized.pop(key))
    if normalized:raise ControllerContractError('Unbound actions '+repr(tuple(normalized)))
    return frame

def observed(context: Any, entity: str, quantity: str):
    name, _, obj=entity.partition('.')
    if not obj:raise ControllerContractError('Native entity must be Class.Name')
    current=context.observation.get('current',{})
    cls=next((v for k,v in current.items() if k.casefold()==name.casefold()),None)
    if cls is None:raise ControllerContractError('Missing observation class '+name)
    record=next((v for k,v in cls.items() if k.casefold()==obj.casefold()),None)
    if record is None or quantity not in record:
        raise ControllerContractError(f'Missing current observation {entity}.{quantity}')
    return record[quantity]

def bound_for(context: Any, entity: str, quantity: str):
    result=[item for item in context.action_layout
            if len(item['path'])==3 and (item['path'][0]+'.'+item['path'][1]).casefold()==entity.casefold()
            and item['path'][2]==quantity]
    if len(result)!=1:raise ControllerContractError(f'Expected one binding for {entity} / {quantity}')
    return result[0]

def require_ready(context: Any, entity: str):
    entries=[d for d in context.devices if d.native_entity.casefold()==entity.casefold()]
    if len(entries)!=1 or entries[0].commandability!='EXTERNAL_READY':
        raise ControllerContractError(f'Action device not positively ready: {entity}')
