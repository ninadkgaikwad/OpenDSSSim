"""A05I6 controller-visible read-only information snapshots.

Official boundary only: this is not a Python security sandbox. It deliberately
contains no backend, state/history reference, or original future-truth tables.
A04 canonical observation/action authority is unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping
import math

from .forecast import ForecastResult


class ControllerInformationError(ValueError):
    """A controller requested information outside its qualified entitlement."""


class ControllerContextUnavailable(ControllerInformationError):
    """No current committed plant snapshot is available."""


def _freeze(value: Any) -> Any:
    """Detach canonical numerics/containers, never store a runtime-backed object."""
    if hasattr(value, 'tolist') and not isinstance(value, (str, bytes)):
        value = value.tolist()
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze(v) for k, v in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, (str, bool, type(None), int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ControllerInformationError('NONFINITE_PUBLIC_CONTEXT')
        return float(value)
    raise ControllerInformationError(f'UNSUPPORTED_PUBLIC_VALUE_TYPE: {type(value).__name__}')


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw(v) for v in value]
    return value


@dataclass(frozen=True, slots=True)
class ControllerDeviceStatus:
    native_entity: str
    present: bool
    enabled: bool | None
    health: str   # FAULTED or UNKNOWN; never infer HEALTHY from missing telemetry
    commandability: str  # EXTERNAL_READY / FAULT_LOCKED / DISABLED / UNKNOWN / NOT_EXTERNAL
    dss_class: str


@dataclass(frozen=True, slots=True)
class ControllerStaticElement:
    native_entity: str
    dss_class: str
    num_phases: int
    terminal_bus_specs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ControllerStaticNetwork:
    circuit_name: str
    inventory_semantic_sha256: str
    buses: tuple[str, ...]
    source_bus_candidates: tuple[str, ...]
    elements: tuple[ControllerStaticElement, ...]


@dataclass(frozen=True, slots=True)
class ControllerContext:
    schema_version: str
    episode_id: str
    completed_steps: int
    decision_time_utc: str
    electrical_sample_time_utc: str
    observation: Mapping[str, Any]
    observation_space_sha256: str | None
    action_space_sha256: str | None
    action_layout: tuple[Mapping[str, Any], ...]
    devices: tuple[ControllerDeviceStatus, ...]
    static_network: ControllerStaticNetwork | None
    last_realized_action_feedback: tuple[Mapping[str, Any], ...]
    forecast: ForecastResult | None

    def to_dict(self) -> dict[str, Any]:
        """Detached JSON-compatible view; mutations never affect simulator state."""
        return {
            'schema_version': self.schema_version,
            'episode_id': self.episode_id,
            'completed_steps': self.completed_steps,
            'decision_time_utc': self.decision_time_utc,
            'electrical_sample_time_utc': self.electrical_sample_time_utc,
            'observation': _thaw(self.observation),
            'observation_space_sha256': self.observation_space_sha256,
            'action_space_sha256': self.action_space_sha256,
            'action_layout': [_thaw(a) for a in self.action_layout],
            'devices': [
                {'native_entity': d.native_entity, 'present': d.present, 'enabled': d.enabled,
                 'health': d.health, 'commandability': d.commandability, 'dss_class': d.dss_class}
                for d in self.devices
            ],
            'static_network': None if self.static_network is None else {
                'circuit_name': self.static_network.circuit_name,
                'inventory_semantic_sha256': self.static_network.inventory_semantic_sha256,
                'buses': list(self.static_network.buses),
                'source_bus_candidates': list(self.static_network.source_bus_candidates),
                'elements': [
                    {'native_entity': e.native_entity, 'dss_class': e.dss_class,
                     'num_phases': e.num_phases, 'terminal_bus_specs': list(e.terminal_bus_specs)}
                    for e in self.static_network.elements
                ],
            },
            'last_realized_action_feedback': [_thaw(a) for a in self.last_realized_action_feedback],
            'forecast': None if self.forecast is None else self.forecast.to_dict(),
        }


def build_controller_context(*, clock: Any, completed_steps: int,
                             observation: Mapping[str, Any], compiled_spaces: Any,
                             runtime_binding: Any, inventory: Any, access: Any,
                             action_audits: tuple[Any, ...], forecast: ForecastResult | None,
                             device_entities: tuple[str, ...] | None = None,
                             include_static_network: bool = True) -> ControllerContext:
    """Build a detached value object from current qualified observations only.

    Live Enabled reads are restricted to entities already selected by A04's
    current observation/action binding, never arbitrary requested native paths.
    """
    metadata = clock.metadata(phase='reset' if completed_steps == 0 else 'step',
                              completed_steps=completed_steps)
    objects = {} if inventory is None else {o.full_name.casefold(): o for o in inventory.objects}
    eligible = {} if runtime_binding is None else {
        b.entry.native_entity.casefold(): b.entry.native_entity
        for b in tuple(runtime_binding.observation_bindings) + tuple(runtime_binding.action_bindings)
        if b.entry.native_entity is not None and b.entry.native_entity.casefold() in objects
    }
    if device_entities is None:
        names = tuple(eligible.values())
    else:
        if isinstance(device_entities, (str, bytes)):
            raise ControllerInformationError('DEVICE_SELECTOR_MUST_BE_SEQUENCE')
        names = tuple(device_entities)
        if any(not isinstance(n, str) or not n for n in names):
            raise ControllerInformationError('INVALID_DEVICE_SELECTOR')
        if len({n.casefold() for n in names}) != len(names):
            raise ControllerInformationError('DUPLICATE_DEVICE_SELECTOR')
        if any(n.casefold() not in eligible for n in names):
            raise ControllerInformationError('DEVICE_NOT_AUTHORIZED_BY_A04')
        names = tuple(eligible[n.casefold()] for n in names)
    faulted = set() if runtime_binding is None else {
        n.casefold() for n in runtime_binding.fault_targets
    }
    external = set() if runtime_binding is None else {
        n.casefold() for n in runtime_binding.resolved_problem.control_authority.external_entities
    }
    device_statuses = []
    for name in sorted(names, key=str.casefold):
        obj = objects.get(name.casefold())
        if obj is None:
            # A04 has validated the binding, so disappearing inventory fails closed.
            raise ControllerInformationError('AUTHORIZED_DEVICE_ABSENT_FROM_INVENTORY')
        enabled = None
        if any(p.casefold() == 'enabled' for p in obj.property_names):
            try:
                from opendsssim.semantics.schema import NativePropertyAddress
                raw = access.read(NativePropertyAddress(obj.full_name, 'Enabled'))
                if hasattr(raw, 'item'):
                    raw = raw.item()
                if not isinstance(raw, (bool, int)) or int(raw) not in (0, 1):
                    raise ValueError('INVALID_ENABLED_READBACK')
                enabled = bool(raw)
            except Exception:
                enabled = None  # UNKNOWN is safer than invented healthy/available
        known_fault = name.casefold() in faulted
        if known_fault:
            commandability = 'FAULT_LOCKED'
        elif name.casefold() not in external:
            commandability = 'NOT_EXTERNAL'
        elif enabled is False:
            commandability = 'DISABLED'
        elif enabled is None:
            commandability = 'UNKNOWN'
        else:
            commandability = 'EXTERNAL_READY'
        device_statuses.append(ControllerDeviceStatus(obj.full_name, True, enabled,
            'FAULTED' if known_fault else 'UNKNOWN', commandability, obj.dss_class))

    network = None
    if include_static_network:
        if inventory is None:
            raise ControllerContextUnavailable('NO_STATIC_CIRCUIT_INVENTORY')
        static_elements = tuple(ControllerStaticElement(
            x.full_name, x.dss_class, int(x.num_phases), tuple(x.terminal_bus_specs)
        ) for x in inventory.elements)
        candidates = tuple(sorted({
            bus.split('.', 1)[0]
            for elem in inventory.elements if elem.dss_class.casefold() == 'vsource'
            for bus in elem.terminal_bus_specs[:1]
        }, key=str.casefold))
        network = ControllerStaticNetwork(inventory.circuit_name,
            inventory.semantic_sha256, tuple(bus.name for bus in inventory.buses),
            candidates, static_elements)

    if compiled_spaces is not None:
        obs_id = compiled_spaces.observation_space_sha256
        act_id = compiled_spaces.action_space_sha256
        layout = tuple(_freeze(entry.to_dict()) for entry in compiled_spaces.action_layout)
    else:
        obs_id = None; act_id = None; layout = ()
    feedback = tuple(_freeze({
        'semantic_id': a.semantic_id, 'native_entity': a.native_entity,
        'status': a.status.value, 'realized_value': a.realized_value,
    }) for a in action_audits)
    return ControllerContext(
        'A05I6.controller-context.v1', str(metadata['episode_id']),
        completed_steps, str(metadata['decision_time_utc']),
        str(metadata['electrical_sample_time_utc']), _freeze(observation),
        obs_id, act_id, layout, tuple(device_statuses), network, feedback, forecast)
