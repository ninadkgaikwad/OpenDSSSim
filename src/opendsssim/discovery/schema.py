"""Typed, immutable discovery snapshots for OpenDSSSim A02."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Any

DISCOVERY_SCHEMA_VERSION = "A02.v1"


@dataclass(frozen=True)
class EngineDiscovery:
    """Read-only description of the owned electrical-engine context."""

    schema_version: str
    backend: str
    altdss_version: str
    engine_version: str
    context_identity: int
    public_api_names: tuple[str, ...]
    feature_flags: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BusDiscovery:
    """One native OpenDSS bus and its discovered node names."""

    name: str
    node_names: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DSSObjectDiscovery:
    """One native DSS object with a canonical full name and property snapshot."""

    full_name: str
    dss_class: str
    name: str
    is_circuit_element: bool
    property_names: tuple[str, ...]
    properties_json: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DSSClassDiscovery:
    """One native DSS class and the objects discovered for that class."""

    dss_class: str
    object_full_names: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CircuitElementDiscovery:
    """Structural metadata for one circuit element."""

    full_name: str
    dss_class: str
    name: str
    num_phases: int
    num_terminals: int
    num_conductors: int
    node_order: tuple[int, ...]
    node_ref: tuple[int, ...]
    terminal_bus_specs: tuple[str, ...]
    has_switch_control: bool
    has_volt_control: bool
    has_ocp_device: bool
    is_isolated: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TopologyDiscovery:
    """Read-only topology summary exposed by the AltDSS Topology interface."""

    isolated_branches: tuple[str, ...]
    isolated_loads: tuple[str, ...]
    looped_pairs: tuple[str, ...]
    num_isolated_branches: int
    num_isolated_loads: int
    num_loops: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CircuitDiscovery:
    """Deterministic discovery snapshot for one loaded circuit."""

    schema_version: str
    source_sha256: str
    circuit_name: str
    num_buses: int
    num_nodes: int
    num_circuit_elements: int
    solution_converged: bool
    engine: EngineDiscovery
    buses: tuple[BusDiscovery, ...]
    node_names: tuple[str, ...]
    classes: tuple[DSSClassDiscovery, ...]
    objects: tuple[DSSObjectDiscovery, ...]
    elements: tuple[CircuitElementDiscovery, ...]
    topology: TopologyDiscovery

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def semantic_dict(self) -> dict[str, Any]:
        """Return context-independent semantic content for replay comparison."""

        payload = self.to_dict()
        payload["engine"] = dict(payload["engine"])
        payload["engine"].pop("context_identity", None)
        return payload

    @property
    def semantic_sha256(self) -> str:
        encoded = json.dumps(
            self.semantic_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return sha256(encoded).hexdigest().upper()

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        ) + "\n"
