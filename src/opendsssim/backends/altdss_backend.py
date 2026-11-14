"""AltDSS backend for the OpenDSSSim A02 discovery foundation."""

from __future__ import annotations

from collections import defaultdict
from importlib.metadata import version as package_version
import json
import math
from numbers import Integral, Real
import re
from typing import Any, Iterable

from altdss import altdss
from dss.enums import DSSJSONFlags, SolveModes

from opendsssim.backends.native_queue_snapshot import collect_control_queue_snapshot

from opendsssim.backends.base import (
    CircuitNotLoadedError,
    DistributionBackend,
    OpenDSSSimBackendError,
)
from opendsssim.discovery.schema import (
    DISCOVERY_SCHEMA_VERSION,
    BusDiscovery,
    CircuitDiscovery,
    CircuitElementDiscovery,
    DSSClassDiscovery,
    DSSObjectDiscovery,
    EngineDiscovery,
    TopologyDiscovery,
)
from opendsssim.network.loading import CircuitIdentity, CircuitSource
from opendsssim.plant.solution import SolutionResult


_DISCOVERY_JSON_FLAGS = (
    DSSJSONFlags.Full
    | DSSJSONFlags.FullNames
    | DSSJSONFlags.IncludeDSSClass
)

_GENERIC_BATCH_NAMES = {"Element", "PCElement", "PDElement"}


# R02A: Full capacitor JSON can expose an unconfigured CMatrix with
# nondeterministic native values. For this class alone, collect explicitly
# configured properties using the native sparse serializer, then augment
# the defined A02/A03 defaults from their public typed native getters.
# Never access the unused CMatrix getter. An explicitly configured CMatrix
# remains in the native sparse JSON and is validated rather than discarded.
_CAPACITOR_READBACK_PROPERTIES = (
    "Bus1", "Bus2", "Phases", "kvar", "kV", "Conn", "Cuf",
    "R", "XL", "Harm", "States", "NormAmps", "EmergAmps",
    "FaultRate", "pctPerm", "Repair", "BaseFreq", "Enabled",
)
_CAPACITOR_SPARSE_FLAGS = DSSJSONFlags.FullNames | DSSJSONFlags.IncludeDSSClass


def _capacitor_safe_value(value: Any, path: str) -> Any:
    """Convert public typed native values to finite JSON primitives only."""

    if hasattr(value, "tolist"):
        value = value.tolist()
    elif hasattr(value, "item") and not isinstance(value, (str, bytes, bool, Real)):
        value = value.item()
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real):
        converted = float(value)
        if not math.isfinite(converted):
            raise OpenDSSSimBackendError(f"Non-finite native capacitor property {path!r}.")
        return converted
    if isinstance(value, (list, tuple)):
        return [_capacitor_safe_value(v, f"{path}[{i}]") for i, v in enumerate(value)]
    raise OpenDSSSimBackendError(
        f"Unsupported native capacitor property type for {path!r}: {type(value).__name__}."
    )


def _read_capacitor_safe_properties(obj: Any, full_name: str) -> dict[str, Any]:
    """Preserve explicit capacitor inputs and stable native defaults, without Full CMatrix."""

    try:
        # Strict JSON: do not accept NaN/Infinity values silently.
        def reject_constant(value: str) -> Any:
            raise ValueError(f"Non-finite JSON token: {value}")

        raw = json.loads(obj.to_json(_CAPACITOR_SPARSE_FLAGS), parse_constant=reject_constant)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise OpenDSSSimBackendError(
            f"Invalid explicitly configured native capacitor JSON for {full_name!r}."
        ) from exc
    if not isinstance(raw, dict):
        raise OpenDSSSimBackendError(f"Expected capacitor JSON object for {full_name!r}.")

    prefix_class, _, prefix_name = full_name.partition(".")
    if prefix_class.casefold() != "capacitor" or not prefix_name:
        raise OpenDSSSimBackendError(f"Not a capacitor object: {full_name!r}.")
    if str(raw.get("Name", prefix_name)).casefold() != prefix_name.casefold():
        raise OpenDSSSimBackendError(f"Native capacitor name mismatch for {full_name!r}.")
    if str(raw.get("DSSClass", "Capacitor")).casefold() != "capacitor":
        raise OpenDSSSimBackendError(f"Native capacitor class mismatch for {full_name!r}.")

    # Do not substitute made-up physical defaults. Each missing field below
    # must be obtained from the current native object; missing getters fail.
    result = {
        str(key): _capacitor_safe_value(value, f"{full_name}.{key}")
        for key, value in raw.items()
    }
    result.setdefault("DSSClass", "Capacitor")
    result.setdefault("Name", prefix_name)
    known = {str(key).casefold() for key in result}
    for property_name in _CAPACITOR_READBACK_PROPERTIES:
        if property_name.casefold() in known:
            continue
        getter = "Conn_str" if property_name == "Conn" else property_name
        try:
            value = getattr(obj, getter)
        except Exception as exc:
            raise OpenDSSSimBackendError(
                f"Missing native capacitor getter {getter!r} for {full_name!r}."
            ) from exc
        result[property_name] = _capacitor_safe_value(value, f"{full_name}.{property_name}")
    # Deliberately absent unless explicitly configured: CMatrix, which has
    # exhibited nondeterministic unused native memory under Full export.
    return result


def _read_discovery_properties(obj: Any, full_name: str) -> dict[str, Any]:
    if full_name.partition(".")[0].casefold() == "capacitor":
        return _read_capacitor_safe_properties(obj, full_name)
    raw = json.loads(obj.to_json(_DISCOVERY_JSON_FLAGS))
    if not isinstance(raw, dict):
        raise OpenDSSSimBackendError(
            f"Expected JSON object for {full_name}; got {type(raw).__name__}."
        )
    return raw


def _casefold_key(value: str) -> tuple[str, str]:
    return (value.casefold(), value)


def _extract_terminal_bus_specs(properties: dict[str, Any]) -> tuple[str, ...]:
    """Extract native bus specifications without interpreting action semantics."""

    entries: list[tuple[tuple[int, int, str], Any]] = []

    for key, value in properties.items():
        lowered = str(key).casefold()

        match = re.fullmatch(r"bus(\d+)", lowered)
        if match:
            entries.append(((0, int(match.group(1)), lowered), value))
            continue

        if lowered == "bus":
            entries.append(((1, 0, lowered), value))
        elif lowered == "buses":
            entries.append(((2, 0, lowered), value))

    values: list[str] = []
    for _, raw_value in sorted(entries, key=lambda item: item[0]):
        if raw_value is None:
            continue

        if isinstance(raw_value, (list, tuple)):
            candidates = raw_value
        else:
            candidates = [raw_value]

        for candidate in candidates:
            text = str(candidate)
            if text and text not in values:
                values.append(text)

    return tuple(values)


class AltDSSBackend(DistributionBackend):
    """One OpenDSSSim backend instance owns one independent AltDSS context."""

    def __init__(self) -> None:
        self._context = altdss.NewContext()
        self._context.Settings.AllowChangeDir = False
        self._loaded_source: CircuitSource | None = None
        self._closed = False
        # S06 general load-service state, isolated to this owned native context.
        # Each record: (uncurtailed P kW, uncurtailed Q kvar, realized fraction).
        self._load_service: dict[str, tuple[float, float, float]] = {}

    def _require_open(self) -> None:
        if self._closed or self._context is None:
            raise OpenDSSSimBackendError("AltDSSBackend is closed.")

    def _require_loaded(self) -> CircuitSource:
        self._require_open()
        if self._loaded_source is None:
            raise CircuitNotLoadedError(
                "Circuit discovery requires a loaded circuit."
            )
        return self._loaded_source

    @property
    def context_identity(self) -> int:
        self._require_open()
        return id(self._context)

    @property
    def engine_version(self) -> str:
        self._require_open()
        return str(self._context.Version())

    @property
    def altdss_package_version(self) -> str:
        return package_version("altdss")

    @property
    def loaded_source(self) -> CircuitSource | None:
        return self._loaded_source

    @property
    def is_closed(self) -> bool:
        return self._closed

    def load_circuit(self, source: CircuitSource) -> CircuitIdentity:
        self._require_open()
        source.validate()

        if '"' in str(source.master_path):
            raise ValueError("DSS master path may not contain a double quote.")

        self._context.ClearAll()
        self._load_service.clear()
        self._context.Settings.AllowChangeDir = False
        self._context(f'Redirect "{source.master_path}"')

        circuit_name = str(self._context.Name or "")
        if not circuit_name:
            raise OpenDSSSimBackendError(
                f"No active circuit was created by DSS master: {source.master_path}"
            )

        self._loaded_source = source

        return CircuitIdentity(
            source=source,
            circuit_name=circuit_name,
            num_buses=int(self._context.NumBuses),
            num_nodes=int(self._context.NumNodes),
            num_circuit_elements=int(self._context.NumCircuitElements),
        )

    def reset_circuit(self) -> CircuitIdentity:
        self._require_open()
        if self._loaded_source is None:
            raise CircuitNotLoadedError("Cannot reset before a circuit has been loaded.")
        return self.load_circuit(self._loaded_source)

    def solve_snapshot(self) -> SolutionResult:
        self._require_open()
        if self._loaded_source is None:
            raise CircuitNotLoadedError("Cannot solve before a circuit has been loaded.")

        solution = self._context.Solution
        solution.Mode = SolveModes.SnapShot
        solution.Solve()

        total_power = complex(self._context.TotalPower())

        return SolutionResult(
            converged=bool(solution.Converged),
            iterations=int(solution.Iterations),
            total_iterations=int(solution.TotalIterations),
            control_iterations=int(solution.ControlIterations),
            process_time_s=float(solution.ProcessTime),
            solve_mode=str(solution.Mode_str),
            circuit_name=str(self._context.Name),
            num_buses=int(self._context.NumBuses),
            num_nodes=int(self._context.NumNodes),
            num_circuit_elements=int(self._context.NumCircuitElements),
            total_power_kw=float(total_power.real),
            total_power_kvar=float(total_power.imag),
            engine_version=str(self._context.Version()),
            altdss_version=self.altdss_package_version,
            context_identity=self.context_identity,
        )

    def discover_engine(self) -> EngineDiscovery:
        """Discover the installed AltDSS surface without mutating circuit physics."""

        self._require_open()

        public_names = tuple(
            sorted(
                (
                    name
                    for name in dir(self._context)
                    if not name.startswith("_")
                ),
                key=str.casefold,
            )
        )

        feature_checks = {
            "bus_inventory": hasattr(self._context, "BusNames"),
            "circuit_element_batch": hasattr(self._context, "Element"),
            "full_property_json": hasattr(self._context, "to_json"),
            "independent_contexts": hasattr(self._context, "NewContext"),
            "node_inventory": hasattr(self._context, "NodeNames"),
            "pc_element_batch": hasattr(self._context, "PCElement"),
            "pd_element_batch": hasattr(self._context, "PDElement"),
            "topology_summary": hasattr(self._context, "Topology"),
        }

        feature_flags = tuple(
            name
            for name, available in sorted(feature_checks.items())
            if available
        )

        return EngineDiscovery(
            schema_version=DISCOVERY_SCHEMA_VERSION,
            backend="altdss",
            altdss_version=self.altdss_package_version,
            engine_version=self.engine_version,
            context_identity=self.context_identity,
            public_api_names=public_names,
            feature_flags=feature_flags,
        )

    def _iter_object_managers(self) -> Iterable[tuple[str, Any]]:
        """Yield typed DSS object managers exposed by this AltDSS context."""

        for attr_name in sorted(dir(self._context), key=str.casefold):
            if attr_name.startswith("_") or attr_name in _GENERIC_BATCH_NAMES:
                continue

            try:
                manager = getattr(self._context, attr_name)
            except Exception:
                continue

            if not hasattr(manager, "__iter__") or not hasattr(manager, "__len__"):
                continue

            try:
                if len(manager) == 0:
                    continue
                first = next(iter(manager))
            except (StopIteration, TypeError):
                continue
            except Exception:
                continue

            if not callable(getattr(first, "FullName", None)):
                continue

            yield attr_name, manager

    def _discover_objects(
        self,
        circuit_element_names: set[str],
    ) -> tuple[DSSObjectDiscovery, ...]:
        discovered: dict[str, DSSObjectDiscovery] = {}

        for _, manager in self._iter_object_managers():
            for obj in manager:
                full_name = str(obj.FullName())
                if not full_name:
                    continue

                raw = _read_discovery_properties(obj, full_name)

                if "." in full_name:
                    prefix_class, prefix_name = full_name.split(".", 1)
                else:
                    prefix_class, prefix_name = "", full_name

                dss_class = str(raw.get("DSSClass") or prefix_class)
                name = str(raw.get("Name") or prefix_name)

                canonical_json = json.dumps(
                    raw,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                )

                key = full_name.casefold()
                discovered[key] = DSSObjectDiscovery(
                    full_name=full_name,
                    dss_class=dss_class,
                    name=name,
                    is_circuit_element=key in circuit_element_names,
                    property_names=tuple(
                        sorted((str(name) for name in raw.keys()), key=str.casefold)
                    ),
                    properties_json=canonical_json,
                )

        return tuple(
            sorted(discovered.values(), key=lambda item: _casefold_key(item.full_name))
        )

    def _discover_elements(
        self,
        object_by_name: dict[str, DSSObjectDiscovery],
    ) -> tuple[CircuitElementDiscovery, ...]:
        elements: list[CircuitElementDiscovery] = []

        for element in self._context.Element:
            full_name = str(element.FullName())
            if "." in full_name:
                dss_class, name = full_name.split(".", 1)
            else:
                dss_class, name = "", full_name

            obj = object_by_name.get(full_name.casefold())
            if obj is not None:
                try:
                    properties = json.loads(obj.properties_json)
                except json.JSONDecodeError:
                    properties = {}
            else:
                properties = {}

            try:
                node_order = tuple(int(value) for value in element.NodeOrder())
            except Exception:
                node_order = ()

            try:
                node_ref = tuple(int(value) for value in element.NodeRef())
            except Exception:
                node_ref = ()

            elements.append(
                CircuitElementDiscovery(
                    full_name=full_name,
                    dss_class=dss_class,
                    name=name,
                    num_phases=int(element.NumPhases()),
                    num_terminals=int(element.NumTerminals()),
                    num_conductors=int(element.NumConductors()),
                    node_order=node_order,
                    node_ref=node_ref,
                    terminal_bus_specs=_extract_terminal_bus_specs(properties),
                    has_switch_control=bool(element.HasSwitchControl()),
                    has_volt_control=bool(element.HasVoltControl()),
                    has_ocp_device=bool(element.HasOCPDevice()),
                    is_isolated=bool(element.IsIsolated()),
                )
            )

        return tuple(
            sorted(elements, key=lambda item: _casefold_key(item.full_name))
        )

    def discover_circuit(self) -> CircuitDiscovery:
        """Return a deterministic, read-only snapshot of the loaded circuit."""

        source = self._require_loaded()

        bus_names = tuple(
            sorted((str(name) for name in self._context.BusNames()), key=str.casefold)
        )
        node_names_engine_order = tuple(
            str(name) for name in self._context.NodeNames()
        )

        bus_lookup = {name.casefold(): name for name in bus_names}
        bus_nodes: dict[str, list[str]] = {name: [] for name in bus_names}

        for node_name in node_names_engine_order:
            if "." not in node_name:
                continue
            candidate = node_name.rsplit(".", 1)[0]
            canonical_bus = bus_lookup.get(candidate.casefold())
            if canonical_bus is not None:
                bus_nodes[canonical_bus].append(node_name)

        buses = tuple(
            BusDiscovery(
                name=bus_name,
                node_names=tuple(bus_nodes[bus_name]),
            )
            for bus_name in bus_names
        )

        raw_element_names = tuple(str(name) for name in self._context.Element.FullName())
        element_name_set = {name.casefold() for name in raw_element_names}

        objects = self._discover_objects(element_name_set)
        object_by_name = {obj.full_name.casefold(): obj for obj in objects}
        elements = self._discover_elements(object_by_name)

        class_members: dict[str, list[str]] = defaultdict(list)
        class_spelling: dict[str, str] = {}

        for obj in objects:
            key = obj.dss_class.casefold()
            class_spelling.setdefault(key, obj.dss_class)
            class_members[key].append(obj.full_name)

        classes = tuple(
            DSSClassDiscovery(
                dss_class=class_spelling[key],
                object_full_names=tuple(
                    sorted(class_members[key], key=str.casefold)
                ),
            )
            for key in sorted(class_members)
        )

        topology = self._context.Topology
        topology_snapshot = TopologyDiscovery(
            isolated_branches=tuple(
                sorted((str(name) for name in topology.AllIsolatedBranches), key=str.casefold)
            ),
            isolated_loads=tuple(
                sorted((str(name) for name in topology.AllIsolatedLoads), key=str.casefold)
            ),
            looped_pairs=tuple(str(name) for name in topology.AllLoopedPairs),
            num_isolated_branches=int(topology.NumIsolatedBranches),
            num_isolated_loads=int(topology.NumIsolatedLoads),
            num_loops=int(topology.NumLoops),
        )

        return CircuitDiscovery(
            schema_version=DISCOVERY_SCHEMA_VERSION,
            source_sha256=source.sha256,
            circuit_name=str(self._context.Name),
            num_buses=int(self._context.NumBuses),
            num_nodes=int(self._context.NumNodes),
            num_circuit_elements=int(self._context.NumCircuitElements),
            solution_converged=bool(self._context.Solution.Converged),
            engine=self.discover_engine(),
            buses=buses,
            node_names=node_names_engine_order,
            classes=classes,
            objects=objects,
            elements=elements,
            topology=topology_snapshot,
        )

    def _resolve_native_object(self, object_full_name: str) -> Any:
        """Resolve one exact native DSS object without broad rediscovery."""

        self._require_loaded()

        if "." not in object_full_name:
            raise OpenDSSSimBackendError(
                f"Expected native full object name Class.Name; got {object_full_name!r}."
            )

        dss_class, object_name = object_full_name.split(".", 1)
        # R02A-R1: discovery consumers may normalize the native class name
        # (e.g. "capacitor.c83"), whereas AltDSS publishes "Capacitor".
        # Canonicalize only this known class; keep all other class lookup
        # behavior and the subsequent exact FullName identity gate intact.
        manager_class = "Capacitor" if dss_class.casefold() == "capacitor" else dss_class
        manager = getattr(self._context, manager_class, None)
        if manager is None or not hasattr(manager, "find"):
            raise OpenDSSSimBackendError(
                f"AltDSS manager not available for class {dss_class!r}."
            )

        try:
            obj = manager.find(object_name)
            resolved_name = str(obj.FullName())
        except Exception as exc:
            raise OpenDSSSimBackendError(
                f"Unable to resolve native object {object_full_name!r}."
            ) from exc

        if resolved_name.casefold() != object_full_name.casefold():
            raise OpenDSSSimBackendError(
                f"Resolved native object mismatch: requested {object_full_name!r}, "
                f"received {resolved_name!r}."
            )
        return obj

    def _native_property_payload(self, object_full_name: str) -> tuple[Any, dict[str, Any]]:
        obj = self._resolve_native_object(object_full_name)
        try:
            raw = _read_discovery_properties(obj, object_full_name)
        except Exception as exc:
            raise OpenDSSSimBackendError(
                f"Unable to read native object properties for {object_full_name!r}."
            ) from exc

        if not isinstance(raw, dict):
            raise OpenDSSSimBackendError(
                f"Expected JSON object for {object_full_name!r}."
            )
        return obj, raw

    @staticmethod
    def _lookup_property(raw: dict[str, Any], property_name: str) -> tuple[str, Any] | None:
        requested = str(property_name).casefold()
        for key, value in raw.items():
            if str(key).casefold() == requested:
                return str(key), value
        return None

    def _resolve_circuit_element(self, entity: str) -> Any:
        obj = self._resolve_native_object(entity)
        required = ("Currents", "TotalPowers", "Losses", "NumTerminals", "IsOpen")
        if not all(callable(getattr(obj, name, None)) for name in required):
            raise OpenDSSSimBackendError(
                f"Native object {entity!r} does not expose the required CircuitElement runtime API."
            )
        return obj

    def _resolve_regulated_tap_winding(self, entity: str) -> int:
        """Resolve the unique RegControl tap winding for an A03 regulator target."""

        if "." not in entity:
            raise OpenDSSSimBackendError(f"Expected transformer full name; got {entity!r}.")
        _, object_name = entity.split(".", 1)

        manager = getattr(self._context, "RegControl", None)
        if manager is None:
            raise OpenDSSSimBackendError(
                f"No RegControl manager is available to resolve tap winding for {entity!r}."
            )

        windings: set[int] = set()
        for control in manager:
            try:
                raw = json.loads(control.to_json(_DISCOVERY_JSON_FLAGS))
            except Exception:
                continue
            if not isinstance(raw, dict):
                continue

            target = raw.get("Transformer")
            if target is None:
                continue
            target_text = str(target)
            candidates = {
                target_text.casefold(),
                f"Transformer.{target_text}".casefold(),
                f"AutoTrans.{target_text}".casefold(),
            }
            if entity.casefold() not in candidates and object_name.casefold() != target_text.casefold():
                continue

            raw_winding = raw.get("TapWinding", raw.get("Winding"))
            if raw_winding is None:
                continue
            try:
                windings.add(int(raw_winding))
            except (TypeError, ValueError):
                continue

        if len(windings) != 1:
            raise OpenDSSSimBackendError(
                f"Expected exactly one regulated tap winding for {entity!r}; found {sorted(windings)}."
            )
        return next(iter(windings))

    def _resolve_switch_terminal(self, entity: str) -> int:
        """Resolve SwtControl terminal when present; otherwise use terminal 1."""

        if "." not in entity:
            raise OpenDSSSimBackendError(f"Expected circuit-element full name; got {entity!r}.")
        _, object_name = entity.split(".", 1)

        manager = getattr(self._context, "SwtControl", None)
        if manager is None:
            return 1

        terminals: set[int] = set()
        for control in manager:
            try:
                raw = json.loads(control.to_json(_DISCOVERY_JSON_FLAGS))
            except Exception:
                continue
            if not isinstance(raw, dict):
                continue

            target = raw.get("SwitchedObj")
            if target is None:
                continue
            target_text = str(target)
            candidates = {
                target_text.casefold(),
                f"Line.{target_text}".casefold(),
            }
            if entity.casefold() not in candidates and object_name.casefold() != target_text.casefold():
                continue

            raw_terminal = raw.get("SwitchedTerm", 1)
            try:
                terminals.add(int(raw_terminal))
            except (TypeError, ValueError):
                continue

        if not terminals:
            return 1
        if len(terminals) != 1:
            raise OpenDSSSimBackendError(
                f"Expected at most one switch terminal for {entity!r}; found {sorted(terminals)}."
            )
        terminal = next(iter(terminals))
        if terminal < 1:
            raise OpenDSSSimBackendError(
                f"Resolved invalid switch terminal {terminal} for {entity!r}."
            )
        return terminal

    def read_object_properties(
        self,
        object_full_name: str,
        property_names: tuple[str, ...],
    ) -> dict[str, Any]:
        """Read an explicit policy-selected subset of native object properties."""

        _, raw = self._native_property_payload(object_full_name)
        result: dict[str, Any] = {}
        for requested in property_names:
            item = self._lookup_property(raw, requested)
            if item is not None:
                actual_name, value = item
                result[actual_name] = value

        return dict(sorted(result.items(), key=lambda item: item[0].casefold()))

    def write_object_property(
        self,
        object_full_name: str,
        property_name: str,
        value: Any,
    ) -> Any:
        """Write one exact native property using the AltDSS object interface."""

        obj, raw = self._native_property_payload(object_full_name)
        item = self._lookup_property(raw, property_name)
        if item is None:
            raise OpenDSSSimBackendError(
                f"Native property {property_name!r} is not available on {object_full_name!r}."
            )
        actual_name, _ = item

        try:
            edit = getattr(obj, "edit", None)
            if callable(edit):
                edit(**{actual_name: value})
            else:
                setattr(obj, actual_name, value)
        except Exception as exc:
            raise OpenDSSSimBackendError(
                f"Unable to write native property {actual_name!r} on {object_full_name!r}."
            ) from exc

        readback = self.read_object_properties(object_full_name, (actual_name,))
        item = next(iter(readback.values()), None)
        if not readback:
            raise OpenDSSSimBackendError(
                f"Unable to read back native property {actual_name!r} on {object_full_name!r}."
            )
        # A05 exogenous load writes are the authoritative *uncurtailed*
        # demand. Invalidate the prior service fraction, updating the one
        # channel written. The paired channel follows on the same A05 step.
        if (object_full_name.partition(".")[0].casefold() == "load"
                and actual_name.casefold() in {"kw", "kvar"}):
            key = object_full_name.casefold()
            old = self._load_service.get(key)
            if old is None:
                p, q = self._native_load_pq(object_full_name)
            else:
                p, q = old[:2]
            numeric = self._load_number(item, label=f"{object_full_name}.{actual_name}")
            if actual_name.casefold() == "kw":
                p = numeric
            else:
                q = numeric
            self._load_service[key] = (p, q, 1.0)
        return item

    @staticmethod
    def _load_number(raw: Any, *, label: str) -> float:
        if isinstance(raw, bool) or not isinstance(raw, Real):
            raise OpenDSSSimBackendError(f"S06_INVALID_LOAD_NUMERIC: {label}")
        number = float(raw)
        if not math.isfinite(number):
            raise OpenDSSSimBackendError(f"S06_NONFINITE_LOAD_NUMERIC: {label}")
        return number

    def _native_load_pq(self, full_name: str) -> tuple[float, float]:
        props = self.read_object_properties(full_name, ("kW", "kvar"))
        by_key = {k.casefold(): v for k, v in props.items()}
        if "kw" not in by_key or "kvar" not in by_key:
            raise OpenDSSSimBackendError(f"S06_LOAD_PQ_NOT_READABLE: {full_name}")
        return (self._load_number(by_key["kw"], label=full_name+".kW"),
                self._load_number(by_key["kvar"], label=full_name+".kvar"))

    def _load_service_record(self, full_name: str) -> tuple[float, float, float]:
        if full_name.partition(".")[0].casefold() != "load":
            raise OpenDSSSimBackendError(f"S06_LOAD_SERVICE_CLASS_MISMATCH: {full_name}")
        # Prove object exists, even when no load-service command has occurred.
        current = self._native_load_pq(full_name)
        record = self._load_service.get(full_name.casefold())
        if record is None:
            return (current[0], current[1], 1.0)
        base_p, base_q, fraction = record
        if not (math.isclose(current[0], base_p*fraction, rel_tol=1e-6, abs_tol=1e-5)
                and math.isclose(current[1], base_q*fraction, rel_tol=1e-6, abs_tol=1e-5)):
            raise OpenDSSSimBackendError(f"S06_LOAD_SERVICE_NATIVE_READBACK_DIVERGED: {full_name}")
        return record

    def read_runtime_channel(
        self,
        service: str,
        entity: str | None,
        channel: str,
    ) -> Any:
        """Read the qualified A03 runtime-readout vocabulary from the live context."""

        self._require_loaded()
        service_key = str(service).casefold()
        channel_key = str(channel).casefold()

        if service_key == "load":
            if entity is None:
                raise OpenDSSSimBackendError("S06_LOAD_SERVICE_REQUIRES_ENTITY")
            base_p, base_q, fraction = self._load_service_record(entity)
            if channel_key == "applied_fraction":
                return fraction
            if channel_key == "demand_base_kw":
                return base_p
            if channel_key == "demand_base_kvar":
                return base_q

        if service_key == "bus":
            if entity is None:
                raise OpenDSSSimBackendError("Bus runtime readout requires an entity name.")
            try:
                bus = self._context.Bus.find(entity)
            except Exception as exc:
                raise OpenDSSSimBackendError(f"Unable to resolve bus {entity!r}.") from exc

            if channel_key == "voltage":
                return tuple(complex(value) for value in bus.Voltages)
            if channel_key == "pu_voltage":
                return tuple(float(abs(complex(value))) for value in bus.puVoltages)

        elif service_key == "circuitelement":
            if entity is None:
                raise OpenDSSSimBackendError("CircuitElement runtime readout requires an entity.")
            element = self._resolve_circuit_element(entity)

            if channel_key == "currents":
                return tuple(complex(value) for value in element.Currents())
            if channel_key == "terminal_power":
                return tuple(complex(value) for value in element.TotalPowers())
            if channel_key == "losses":
                return complex(element.Losses())
            if channel_key == "open_state":
                return tuple(
                    bool(element.IsOpen(terminal, 0))
                    for terminal in range(1, int(element.NumTerminals()) + 1)
                )

        elif service_key in {"transformer", "autotrans"}:
            if entity is None:
                raise OpenDSSSimBackendError(f"{service} runtime readout requires an entity.")
            obj = self._resolve_native_object(entity)
            if channel_key == "taps":
                try:
                    return tuple(float(value) for value in obj.Taps)
                except Exception as exc:
                    raise OpenDSSSimBackendError(
                        f"Unable to read transformer taps for {entity!r}."
                    ) from exc

        elif service_key == "solution":
            if entity is not None:
                raise OpenDSSSimBackendError("Solution runtime readout does not accept an entity.")
            if channel_key == "converged":
                return bool(self._context.Solution.Converged)

        elif service_key == "topology":
            if entity is not None:
                raise OpenDSSSimBackendError("Topology runtime readout does not accept an entity.")
            if channel_key == "connectivity":
                topology = self._context.Topology
                return {
                    "isolated_branches": tuple(
                        sorted((str(name) for name in topology.AllIsolatedBranches), key=str.casefold)
                    ),
                    "isolated_loads": tuple(
                        sorted((str(name) for name in topology.AllIsolatedLoads), key=str.casefold)
                    ),
                    "looped_pairs": tuple(str(name) for name in topology.AllLoopedPairs),
                    "num_isolated_branches": int(topology.NumIsolatedBranches),
                    "num_isolated_loads": int(topology.NumIsolatedLoads),
                    "num_loops": int(topology.NumLoops),
                }

        raise OpenDSSSimBackendError(
            f"Unsupported A03 runtime readout: service={service!r}, entity={entity!r}, channel={channel!r}."
        )

    def apply_runtime_command(
        self,
        service: str,
        entity: str,
        operation: str,
        value: Any,
    ) -> Any:
        """Apply the qualified A03 runtime-command vocabulary to the live context."""

        self._require_loaded()
        service_key = str(service).casefold()
        operation_key = str(operation).casefold()

        if service_key == "load" and operation_key == "set_served_fraction":
            fraction = self._load_number(value, label=f"{entity}.served_fraction")
            if not 0.0 <= fraction <= 1.0:
                raise OpenDSSSimBackendError(f"S06_LOAD_SERVICE_OUT_OF_DOMAIN: {entity}")
            base_p, base_q, _ = self._load_service_record(entity)
            obj = self._resolve_native_object(entity)
            if entity.partition(".")[0].casefold() != "load":
                raise OpenDSSSimBackendError(f"S06_LOAD_SERVICE_CLASS_MISMATCH: {entity}")
            try:
                obj.edit(kW=base_p * fraction, kvar=base_q * fraction)
            except Exception as exc:
                raise OpenDSSSimBackendError(
                    f"S06_LOAD_SERVICE_WRITE_FAILED: {entity}") from exc
            got_p, got_q = self._native_load_pq(entity)
            if not (math.isclose(got_p, base_p * fraction, rel_tol=1e-6, abs_tol=1e-5)
                    and math.isclose(got_q, base_q * fraction, rel_tol=1e-6, abs_tol=1e-5)):
                raise OpenDSSSimBackendError(f"S06_LOAD_SERVICE_WRITE_READBACK_MISMATCH: {entity}")
            self._load_service[entity.casefold()] = (base_p, base_q, fraction)
            return fraction

        if service_key in {"transformer", "autotrans"} and operation_key == "set_tap":
            obj = self._resolve_native_object(entity)
            try:
                taps = [float(item) for item in obj.Taps]
            except Exception as exc:
                raise OpenDSSSimBackendError(
                    f"Unable to read transformer taps before command for {entity!r}."
                ) from exc

            winding = self._resolve_regulated_tap_winding(entity)
            if winding < 1 or winding > len(taps):
                raise OpenDSSSimBackendError(
                    f"Resolved tap winding {winding} is outside available Taps array for {entity!r}."
                )

            try:
                taps[winding - 1] = float(value)
                obj.edit(Taps=taps)
            except Exception as exc:
                raise OpenDSSSimBackendError(
                    f"Unable to apply set_tap command to {entity!r}."
                ) from exc

            return self.read_runtime_channel(service, entity, "taps")

        if service_key == "circuitelement" and operation_key == "open_close":
            element = self._resolve_circuit_element(entity)
            if isinstance(value, bool):
                state = "CLOSED" if value else "OPEN"
            elif isinstance(value, Integral) and int(value) in (0, 1):
                state = "CLOSED" if int(value) == 1 else "OPEN"
            else:
                state = str(value).strip().upper()

            if state not in {"OPEN", "CLOSED"}:
                raise OpenDSSSimBackendError(
                    f"open_close command requires OPEN/CLOSED (or 0/1); got {value!r}."
                )

            terminal = self._resolve_switch_terminal(entity)
            try:
                if state == "OPEN":
                    element.Open(terminal, 0)
                else:
                    element.Close(terminal, 0)
            except Exception as exc:
                raise OpenDSSSimBackendError(
                    f"Unable to apply {state} command to {entity!r}."
                ) from exc

            return self.read_runtime_channel("CircuitElement", entity, "open_state")

        raise OpenDSSSimBackendError(
            f"Unsupported A03 runtime command: service={service!r}, entity={entity!r}, "
            f"operation={operation!r}."
        )

    def native_diagnostic_snapshot(self) -> dict[str, Any]:
        """Opt-in detached, read-only diagnostic of the authoritative solved context.

        B00 research/qualification only. Does not solve, alter a DSS property,
        pop the queue, manipulate event state, or publish controller authority.
        """
        self._require_loaded()
        sol = self._context.Solution
        # Underlying AltDSS returns ControlModes (IntEnum), not a DSS text
        # setting. Record both the typed value and engine readback.
        cm = sol.ControlMode
        mode = getattr(cm, "name", None) or str(cm)
        if isinstance(cm, Integral):
            mode_value = int(cm)
        else:
            raise OpenDSSSimBackendError("NATIVE_CONTROL_MODE_UNRECOGNIZED")
        mode_name = {0: "STATIC", 1: "EVENT", 2: "TIME", 3: "MULTIRATE"}.get(mode_value, "UNKNOWN")
        circuit_losses = complex(self._context.Losses())
        if not all(math.isfinite(x) for x in (circuit_losses.real, circuit_losses.imag)):
            raise OpenDSSSimBackendError("NONFINITE_CIRCUIT_LOSSES")
        native_regulators: list[dict[str, Any]] = []
        for obj in self._context.RegControl:
            full = str(obj.FullName())
            if not full.casefold().startswith("regcontrol."):
                raise OpenDSSSimBackendError("REGCONTROL_IDENTITY_INVALID")
            enabled_raw = obj.Enabled
            if not isinstance(enabled_raw, (bool, Integral)) or int(enabled_raw) not in (0,1):
                raise OpenDSSSimBackendError(f"REGCONTROL_ENABLED_NOT_BOOLEAN: {full}")
            settings: dict[str, Any] = {}
            for attr in ("VReg", "Band", "Delay", "TapDelay", "MaxTapChange", "TapWinding"):
                try:
                    value = getattr(obj, attr)
                    if isinstance(value, Integral):
                        settings[attr] = int(value)
                    elif isinstance(value, Real):
                        f = float(value)
                        settings[attr] = f if math.isfinite(f) else None
                    else:
                        settings[attr] = None
                except (AttributeError, TypeError, ValueError):
                    settings[attr] = None
            native_regulators.append({"native_entity": full, "enabled": bool(enabled_raw), "settings": settings})
        native_regulators.sort(key=lambda r:r["native_entity"].casefold())
        if len({r["native_entity"].casefold() for r in native_regulators}) != len(native_regulators):
            raise OpenDSSSimBackendError("DUPLICATE_REGCONTROL_NATIVE_IDENTITY")
        # Read-only native display snapshot; a zero-action queue may render as
        # ["No events"]. It is NOT an action row and must not be popped.
        try:
            queue_snapshot = collect_control_queue_snapshot(self._context.ControlQueue, sol)
        except (ValueError, TypeError) as exc:
            raise OpenDSSSimBackendError(f"INVALID_NATIVE_QUEUE_READBACK: {exc}") from exc
        return {
            "schema": "B00I2.native_diagnostics.v01",
            "context_identity": self.context_identity,
            "solution": {
                "control_mode_value": mode_value,
                "control_mode_name": mode_name,
                "control_mode_enum": str(mode),
                "solve_mode": str(sol.Mode_str),
                "max_control_iterations": int(sol.MaxControlIterations),
                "control_iterations": int(sol.ControlIterations),
                "control_actions_done": bool(sol.ControlActionsDone),
                "hour": int(sol.Hour), "seconds": float(sol.Seconds),
                "step_size_seconds": float(sol.StepSize),
            },
            "regcontrols": native_regulators,
            "losses": {"p_kw": float(circuit_losses.real / 1000.0),
                       "q_kvar": float(circuit_losses.imag / 1000.0),
                       "source": "Altdss.AltDSS.Losses_W_var"},
            "control_queue": queue_snapshot,
        }

    def close(self) -> None:
        if self._closed:
            return
        if self._context is not None:
            try:
                self._context.ClearAll()
            finally:
                self._context = None
        self._loaded_source = None
        self._closed = True
