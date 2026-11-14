"""Native OpenDSS control/protection relationship discovery for A02H1."""

from __future__ import annotations

import json
from typing import Iterable, Sequence

from opendsssim.discovery.schema import CircuitDiscovery, DSSObjectDiscovery
from opendsssim.persistence.inventory_schema import (
    NativeControlObject,
    NativeControlRelationship,
)

# Official DSS-Extensions Control Elements catalog, frozen for A02H1 v1.
NATIVE_CONTROL_CLASSES = (
    "CapControl",
    "ESPVLControl",
    "ExpControl",
    "Fuse",
    "GenDispatcher",
    "InvControl",
    "Recloser",
    "RegControl",
    "Relay",
    "StorageController",
    "SwtControl",
    "UPFCControl",
)

_CONTROL_CLASS_KEYS = {name.casefold(): name for name in NATIVE_CONTROL_CLASSES}


def _property_lookup(properties: dict[str, object], name: str) -> object | None:
    target = name.casefold()
    for key, value in properties.items():
        if str(key).casefold() == target:
            return value
    return None


def _as_strings(value: object | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        text = value.strip()
        return (text,) if text else ()
    if isinstance(value, (list, tuple)):
        values: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                values.append(text)
        return tuple(values)
    text = str(value).strip()
    return (text,) if text else ()


def _as_int(value: object | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _object_indexes(
    objects: Sequence[DSSObjectDiscovery],
) -> tuple[
    dict[str, DSSObjectDiscovery],
    dict[str, tuple[DSSObjectDiscovery, ...]],
]:
    by_full = {obj.full_name.casefold(): obj for obj in objects}

    by_name_lists: dict[str, list[DSSObjectDiscovery]] = {}
    for obj in objects:
        by_name_lists.setdefault(obj.name.casefold(), []).append(obj)

    by_name = {
        key: tuple(
            sorted(values, key=lambda item: item.full_name.casefold())
        )
        for key, values in by_name_lists.items()
    }
    return by_full, by_name


def _resolve_reference(
    reference: str,
    *,
    by_full: dict[str, DSSObjectDiscovery],
    by_name: dict[str, tuple[DSSObjectDiscovery, ...]],
    class_hints: Iterable[str] = (),
) -> tuple[str | None, str, str]:
    """Resolve a native reference without inventing a replacement vocabulary."""

    raw = reference.strip()
    if not raw:
        return None, "OBJECT", "EMPTY"

    direct = by_full.get(raw.casefold())
    if direct is not None:
        return direct.full_name, "OBJECT", "EXPLICIT_RESOLVED"

    for class_hint in class_hints:
        candidate = f"{class_hint}.{raw}"
        direct = by_full.get(candidate.casefold())
        if direct is not None:
            return direct.full_name, "OBJECT", "EXPLICIT_RESOLVED"

    candidates = by_name.get(raw.casefold(), ())
    if len(candidates) == 1:
        return candidates[0].full_name, "OBJECT", "EXPLICIT_RESOLVED"

    return None, "OBJECT", "EXPLICIT_UNRESOLVED"


def _relationship(
    *,
    source: DSSObjectDiscovery,
    role: str,
    property_name: str,
    reference: str,
    by_full: dict[str, DSSObjectDiscovery],
    by_name: dict[str, tuple[DSSObjectDiscovery, ...]],
    class_hints: Iterable[str] = (),
    resolution_override: str | None = None,
    target_kind: str = "OBJECT",
    terminal: int | None = None,
    winding: int | None = None,
    tap_winding: int | None = None,
) -> NativeControlRelationship:
    if target_kind == "BUS":
        target_full_name = None
        resolution = resolution_override or "EXPLICIT_BUS_REFERENCE"
    elif target_kind == "SCOPE":
        target_full_name = None
        resolution = resolution_override or "ENGINE_DEFAULT_SCOPE"
    else:
        target_full_name, _, resolution = _resolve_reference(
            reference,
            by_full=by_full,
            by_name=by_name,
            class_hints=class_hints,
        )
        if resolution_override is not None:
            resolution = resolution_override

    return NativeControlRelationship(
        source_full_name=source.full_name,
        source_class=source.dss_class,
        role=role,
        property_name=property_name,
        target_reference=reference,
        target_full_name=target_full_name,
        target_kind=target_kind,
        resolution=resolution,
        terminal=terminal,
        winding=winding,
        tap_winding=tap_winding,
    )


def _relationships_for_control(
    source: DSSObjectDiscovery,
    properties: dict[str, object],
    objects: Sequence[DSSObjectDiscovery],
    by_full: dict[str, DSSObjectDiscovery],
    by_name: dict[str, tuple[DSSObjectDiscovery, ...]],
) -> list[NativeControlRelationship]:
    relationships: list[NativeControlRelationship] = []
    cls = source.dss_class.casefold()

    def add_single(
        role: str,
        property_name: str,
        *,
        class_hints: tuple[str, ...] = (),
        terminal_property: str | None = None,
        winding_property: str | None = None,
        tap_winding_property: str | None = None,
        target_kind: str = "OBJECT",
    ) -> None:
        values = _as_strings(_property_lookup(properties, property_name))
        if not values:
            return
        reference = values[0]
        relationships.append(
            _relationship(
                source=source,
                role=role,
                property_name=property_name,
                reference=reference,
                by_full=by_full,
                by_name=by_name,
                class_hints=class_hints,
                target_kind=target_kind,
                terminal=(
                    _as_int(_property_lookup(properties, terminal_property))
                    if terminal_property
                    else None
                ),
                winding=(
                    _as_int(_property_lookup(properties, winding_property))
                    if winding_property
                    else None
                ),
                tap_winding=(
                    _as_int(_property_lookup(properties, tap_winding_property))
                    if tap_winding_property
                    else None
                ),
            )
        )

    def add_list(
        role: str,
        property_name: str,
        *,
        class_hints: tuple[str, ...] = (),
    ) -> bool:
        values = _as_strings(_property_lookup(properties, property_name))
        for reference in values:
            relationships.append(
                _relationship(
                    source=source,
                    role=role,
                    property_name=property_name,
                    reference=reference,
                    by_full=by_full,
                    by_name=by_name,
                    class_hints=class_hints,
                )
            )
        return bool(values)

    def add_default_all(
        role: str,
        property_name: str,
        target_classes: tuple[str, ...],
        *,
        resolution: str = "ENGINE_DEFAULT_ALL",
    ) -> None:
        class_keys = {item.casefold() for item in target_classes}
        for target in sorted(objects, key=lambda item: item.full_name.casefold()):
            if target.dss_class.casefold() not in class_keys:
                continue
            relationships.append(
                NativeControlRelationship(
                    source_full_name=source.full_name,
                    source_class=source.dss_class,
                    role=role,
                    property_name=property_name,
                    target_reference=target.full_name,
                    target_full_name=target.full_name,
                    target_kind="OBJECT",
                    resolution=resolution,
                )
            )

    if cls == "regcontrol":
        add_single(
            "CONTROLS",
            "Transformer",
            class_hints=("Transformer", "AutoTrans"),
            winding_property="Winding",
            tap_winding_property="TapWinding",
        )
        add_single("MONITORS_BUS", "Bus", target_kind="BUS")

    elif cls == "capcontrol":
        add_single(
            "MONITORS",
            "Element",
            terminal_property="Terminal",
        )
        add_single(
            "CONTROLS",
            "Capacitor",
            class_hints=("Capacitor",),
        )

    elif cls == "invcontrol":
        if not add_list(
            "CONTROLS",
            "DERList",
            class_hints=("PVSystem", "Storage"),
        ):
            add_default_all(
                "CONTROLS",
                "DERList",
                ("PVSystem", "Storage"),
            )
        for bus in _as_strings(_property_lookup(properties, "MonBus")):
            relationships.append(
                _relationship(
                    source=source,
                    role="MONITORS_BUS",
                    property_name="MonBus",
                    reference=bus,
                    by_full=by_full,
                    by_name=by_name,
                    target_kind="BUS",
                )
            )

    elif cls == "expcontrol":
        explicit = add_list(
            "CONTROLS",
            "DERList",
            class_hints=("PVSystem",),
        )
        if not explicit:
            explicit = add_list(
                "CONTROLS",
                "PVSystemList",
                class_hints=("PVSystem",),
            )
        if not explicit:
            add_default_all(
                "CONTROLS",
                "PVSystemList",
                ("PVSystem",),
            )

    elif cls == "upfccontrol":
        if not add_list(
            "CONTROLS",
            "UPFCList",
            class_hints=("UPFC",),
        ):
            add_default_all(
                "CONTROLS",
                "UPFCList",
                ("UPFC",),
            )

    elif cls == "gendispatcher":
        add_single(
            "MONITORS",
            "Element",
            terminal_property="Terminal",
        )
        if not add_list(
            "CONTROLS",
            "GenList",
            class_hints=("Generator",),
        ):
            add_default_all(
                "CONTROLS",
                "GenList",
                ("Generator",),
            )

    elif cls == "storagecontroller":
        add_single(
            "MONITORS",
            "Element",
            terminal_property="Terminal",
        )
        if not add_list(
            "CONTROLS",
            "ElementList",
            class_hints=("Storage",),
        ):
            add_default_all(
                "CONTROLS",
                "ElementList",
                ("Storage",),
                resolution="ENGINE_DEFAULT_CANDIDATE_UNASSIGNED",
            )

    elif cls == "espvlcontrol":
        add_single(
            "MONITORS",
            "Element",
            terminal_property="Terminal",
        )
        add_list(
            "COORDINATES_CONTROL",
            "LocalControlList",
            class_hints=NATIVE_CONTROL_CLASSES,
        )
        add_list(
            "CONTROLS",
            "PVSystemList",
            class_hints=("PVSystem",),
        )
        add_list(
            "CONTROLS",
            "StorageList",
            class_hints=("Storage",),
        )

    elif cls == "swtcontrol":
        add_single(
            "SWITCHES",
            "SwitchedObj",
            terminal_property="SwitchedTerm",
        )

    elif cls in {"relay", "recloser", "fuse"}:
        add_single(
            "MONITORS",
            "MonitoredObj",
            terminal_property="MonitoredTerm",
        )
        monitored_values = _as_strings(
            _property_lookup(properties, "MonitoredObj")
        )
        switched_values = _as_strings(
            _property_lookup(properties, "SwitchedObj")
        )

        if switched_values:
            add_single(
                "PROTECTS",
                "SwitchedObj",
                terminal_property="SwitchedTerm",
            )
        elif monitored_values:
            reference = monitored_values[0]
            target_full_name, _, _ = _resolve_reference(
                reference,
                by_full=by_full,
                by_name=by_name,
            )
            relationships.append(
                NativeControlRelationship(
                    source_full_name=source.full_name,
                    source_class=source.dss_class,
                    role="PROTECTS",
                    property_name="SwitchedObj",
                    target_reference=reference,
                    target_full_name=target_full_name,
                    target_kind="OBJECT",
                    resolution="ENGINE_DEFAULT_MONITORED_OBJECT",
                    terminal=_as_int(
                        _property_lookup(properties, "SwitchedTerm")
                    ),
                )
            )

    return relationships


def discover_native_controls(
    discovery: CircuitDiscovery,
) -> tuple[
    tuple[NativeControlObject, ...],
    tuple[NativeControlRelationship, ...],
]:
    """Derive static native-control relationships from frozen A02 discovery.

    This function is intentionally offline with respect to AltDSS. It consumes
    the A02 full object snapshot, preserving the A02 read-only boundary.
    """

    objects = tuple(discovery.objects)
    by_full, by_name = _object_indexes(objects)

    controls: list[NativeControlObject] = []
    relationships: list[NativeControlRelationship] = []

    for obj in objects:
        canonical_class = _CONTROL_CLASS_KEYS.get(obj.dss_class.casefold())
        if canonical_class is None:
            continue

        controls.append(
            NativeControlObject(
                full_name=obj.full_name,
                dss_class=obj.dss_class,
                name=obj.name,
                property_names=obj.property_names,
            )
        )

        try:
            properties = json.loads(obj.properties_json)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid A02 property JSON for native control {obj.full_name}"
            ) from exc

        if not isinstance(properties, dict):
            raise ValueError(
                f"Expected mapping property JSON for native control {obj.full_name}"
            )

        relationships.extend(
            _relationships_for_control(
                obj,
                properties,
                objects,
                by_full,
                by_name,
            )
        )

    controls_tuple = tuple(
        sorted(controls, key=lambda item: item.full_name.casefold())
    )
    relationships_tuple = tuple(
        sorted(
            relationships,
            key=lambda item: (
                item.source_full_name.casefold(),
                item.role.casefold(),
                item.property_name.casefold(),
                item.target_reference.casefold(),
            ),
        )
    )

    return controls_tuple, relationships_tuple
