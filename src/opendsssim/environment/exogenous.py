"""A05I2 explicit in-memory physical truth and allowlisted native bindings.

No CSV/Parquet, replay, lookahead, noise, controller forecast or topology event
is implemented here. A05I3 supplies qualified indexing/replay later.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
import math
from typing import Any, Mapping

from opendsssim.persistence.inventory_schema import CircuitInventory
from opendsssim.semantics.schema import (
    Mutability, NativePropertyAddress, SemanticRegistryBundle,
)
from opendsssim.runtime.access import SemanticRuntimeAccess


A05_PV_TEMPERATURE_EXTENSION = "A05I2.pv-temperature-whitelist.v1"
A05_PV_TEMPERATURE_EXTENSION_SHA256 = sha256(
    b"A05I2.pv-temperature-whitelist.v1|PVSystem.Temperature|STEP_EXOGENOUS|degC|" 
    b"physical truth only|not A04 controller action"
).hexdigest().upper()


class ExogenousBindingError(ValueError):
    """Invalid typed physical source, unit, inventory binding or A03 authority."""


class ExogenousApplicationError(RuntimeError):
    """Exogenous read/write/readback failure; episode must be reset."""


def _number(value: Any, label: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExogenousBindingError(f"{label} must be a real, non-boolean scalar")
    v = float(value)
    if not math.isfinite(v) or (minimum is not None and v < minimum):
        raise ExogenousBindingError(f"{label} must be finite and >= {minimum}")
    return v


def _targets(value: Any, label: str) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, (tuple, list)) or not value:
        raise ExogenousBindingError(f"{label} must be a nonempty tuple/list of explicit Class.Name strings")
    ret = tuple(value)
    if any(not isinstance(v, str) or "." not in v or not v.strip() for v in ret):
        raise ExogenousBindingError(f"{label} contains an invalid native object name")
    if len({v.casefold() for v in ret}) != len(ret):
        raise ExogenousBindingError(f"{label} contains duplicate native objects")
    return ret


@dataclass(frozen=True, slots=True)
class LoadSeries:
    """Physical samples: 'absolute_pq', 'multiplier', or 'p_signed_pf'.

    Each point is (kW,kvar), dimensionless multiplier, or (kW,signed PF),
    respectively. Native aggregate phase properties are not phase-disaggregated.
    """
    targets: tuple[str, ...]
    mode: str
    points: tuple[Any, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "targets", _targets(self.targets, "LoadSeries.targets"))
        if self.mode not in {"absolute_pq", "multiplier", "p_signed_pf"}:
            raise ExogenousBindingError(f"unsupported load mode: {self.mode!r}")
        if not isinstance(self.points, (tuple, list)) or not self.points:
            raise ExogenousBindingError("LoadSeries requires at least one physical sample")
        rows = []
        for index, point in enumerate(self.points):
            label = f"LoadSeries.points[{index}]"
            if self.mode == "multiplier":
                rows.append(_number(point, label, minimum=0))
            else:
                if not isinstance(point, (list, tuple)) or len(point) != 2:
                    raise ExogenousBindingError(f"{label} requires exactly two values")
                p = _number(point[0], f"{label}[0]", minimum=0)
                second = _number(point[1], f"{label}[1]")
                if self.mode == "p_signed_pf" and not (0 < abs(second) <= 1):
                    raise ExogenousBindingError("signed PF must satisfy 0 < |pf| <= 1")
                rows.append((p, second))
        object.__setattr__(self, "points", tuple(rows))


@dataclass(frozen=True, slots=True)
class PVSeries:
    """POA/native irradiance in kW/m2; optional paired ambient/wind for Faiman."""
    targets: tuple[str, ...]
    irradiance_kw_m2: tuple[float, ...]
    outdoor_temperature_c: tuple[float, ...] | None = None
    wind_speed_m_s: tuple[float, ...] | None = None
    u0: float = 25.0
    u1: float = 6.84

    def __post_init__(self) -> None:
        object.__setattr__(self, "targets", _targets(self.targets, "PVSeries.targets"))
        if not isinstance(self.irradiance_kw_m2, (tuple, list)) or not self.irradiance_kw_m2:
            raise ExogenousBindingError("PVSeries requires at least one irradiance sample")
        irradiance = tuple(_number(x, "irradiance_kw_m2", minimum=0) for x in self.irradiance_kw_m2)
        object.__setattr__(self, "irradiance_kw_m2", irradiance)
        if (self.outdoor_temperature_c is None) != (self.wind_speed_m_s is None):
            raise ExogenousBindingError("ambient temperature and wind must be both unbound or both bound")
        if self.outdoor_temperature_c is not None:
            if not isinstance(self.outdoor_temperature_c, (list, tuple)) or not isinstance(self.wind_speed_m_s, (list, tuple)):
                raise ExogenousBindingError("bound Faiman weather must be explicit sample tuples")
            if len(self.outdoor_temperature_c) != len(irradiance) or len(self.wind_speed_m_s) != len(irradiance):
                raise ExogenousBindingError("Faiman weather and irradiance lengths must match")
            object.__setattr__(self, "outdoor_temperature_c", tuple(_number(x, "outdoor_temperature_c") for x in self.outdoor_temperature_c))
            object.__setattr__(self, "wind_speed_m_s", tuple(_number(x, "wind_speed_m_s", minimum=0) for x in self.wind_speed_m_s))
        u0 = _number(self.u0, "Faiman u0", minimum=0)
        u1 = _number(self.u1, "Faiman u1", minimum=0)
        if u0 <= 0:
            raise ExogenousBindingError("Faiman u0 must be strictly positive")
        object.__setattr__(self, "u0", u0)
        object.__setattr__(self, "u1", u1)


@dataclass(frozen=True, slots=True)
class ExogenousProfileSpec:
    """An explicit finite series already aligned by its caller.

    A05I3 will later add CSV/Parquet, timezone alignment, strict/tile replay.
    V1 here never silently cycles or interpolates a missing physical sample.
    """
    source_id: str
    loads: tuple[LoadSeries, ...] = ()
    pvs: tuple[PVSeries, ...] = ()
    source_sha256: str = field(init=False)
    sample_count: int = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise ExogenousBindingError("source_id must be nonempty")
        if not isinstance(self.loads, (tuple, list)) or not isinstance(self.pvs, (tuple, list)):
            raise ExogenousBindingError("loads/pvs must be tuples of typed physical series")
        loads, pvs = tuple(self.loads), tuple(self.pvs)
        if any(not isinstance(x, LoadSeries) for x in loads) or any(not isinstance(x, PVSeries) for x in pvs):
            raise ExogenousBindingError("loads and pvs require LoadSeries/PVSeries instances")
        if not loads and not pvs:
            raise ExogenousBindingError("ExogenousProfileSpec must bind at least one device")
        lengths = {len(x.points) for x in loads} | {len(x.irradiance_kw_m2) for x in pvs}
        if len(lengths) != 1:
            raise ExogenousBindingError("all A05I2 physical series must have identical sample count")
        seen: set[str] = set()
        for group in (*loads, *pvs):
            for target in group.targets:
                if target.casefold() in seen:
                    raise ExogenousBindingError(f"ambiguous exogenous writers for {target}")
                seen.add(target.casefold())
        object.__setattr__(self, "loads", loads)
        object.__setattr__(self, "pvs", pvs)
        object.__setattr__(self, "sample_count", next(iter(lengths)))
        data = {"schema": "A05I2.explicit-physical-source.v1", "source_id": self.source_id,
                "loads": [{"targets": x.targets, "mode": x.mode, "points": x.points} for x in loads],
                "pvs": [{"targets": x.targets, "irradiance_kw_m2": x.irradiance_kw_m2,
                         "outdoor_temperature_c": x.outdoor_temperature_c,
                         "wind_speed_m_s": x.wind_speed_m_s, "u0": x.u0, "u1": x.u1} for x in pvs]}
        object.__setattr__(self, "source_sha256", sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest().upper())


class PhysicalExogenousBinding:
    """One-plant narrow A05I2 exogenous writer; never part of controller actions."""

    def __init__(self, spec: ExogenousProfileSpec, inventory: CircuitInventory,
                 semantics: SemanticRegistryBundle, access: SemanticRuntimeAccess,
                 action_addresses: tuple[NativePropertyAddress, ...] = ()) -> None:
        self.spec = spec
        self._access = access
        objects = {o.full_name.casefold(): o for o in inventory.objects}
        allowed = {
            (e.address.object_full_name.casefold(), e.address.property_name.casefold())
            for e in semantics.semantic_entries
            if isinstance(e.address, NativePropertyAddress) and e.mutability is Mutability.STEP_EXOGENOUS
        }
        actions = {(a.object_full_name.casefold(), a.property_name.casefold()) for a in action_addresses}
        self._names: dict[str, str] = {}
        self._baseline: dict[str, tuple[float, float]] = {}
        self._temperature_extension: list[str] = []
        for load in spec.loads:
            for raw in load.targets:
                native, props = self._validate_object(raw, "Load", objects)
                for name in ("kw", "kvar"):
                    self._check_semantic(native, name, props, allowed, actions)
                values = self._access.backend.read_object_properties(native, ("kW", "kvar"))
                keyed = {k.casefold(): v for k, v in values.items()}
                try:
                    self._baseline[native] = (_number(keyed["kw"], f"{native} baseline kW", minimum=0),
                                              _number(keyed["kvar"], f"{native} baseline kvar"))
                except (KeyError, ValueError) as exc:
                    raise ExogenousBindingError(f"Cannot capture a physical baseline for {native}") from exc
        for pv in spec.pvs:
            for raw in pv.targets:
                native, props = self._validate_object(raw, "PVSystem", objects)
                self._check_semantic(native, "irradiance", props, allowed, actions)
                # A03 has no PVSystem.Temperature exogenous semantic. A05 is an
                # explicit extension and is never exposed as an A04 action.
                if "temperature" not in props:
                    raise ExogenousBindingError(f"PVSystem.Temperature is not supported for {native}")
                if (native.casefold(), "temperature") in actions:
                    raise ExogenousBindingError(f"PV temperature conflicts with controller action: {native}")
                self._temperature_extension.append(native)
        self._temperature_extension = sorted(self._temperature_extension, key=str.casefold)

    def _validate_object(self, raw: str, cls: str, objects: Mapping[str, Any]) -> tuple[str, set[str]]:
        obj = objects.get(raw.casefold())
        if obj is None or obj.dss_class.casefold() != cls.casefold():
            raise ExogenousBindingError(f"Unknown or wrong-class physical endpoint: {raw}")
        self._names[raw.casefold()] = obj.full_name
        return obj.full_name, {name.casefold() for name in obj.property_names}

    @staticmethod
    def _check_semantic(native: str, property_name: str, props: set[str], allowed: set[tuple[str, str]],
                        actions: set[tuple[str, str]]) -> None:
        key = (native.casefold(), property_name)
        if property_name not in props or key not in allowed:
            raise ExogenousBindingError(f"No frozen A03 STEP_EXOGENOUS authority for {native}.{property_name}")
        if key in actions:
            raise ExogenousBindingError(f"Controller/exogenous native-property writer conflict: {native}.{property_name}")

    def _pair(self, load: LoadSeries, native: str, index: int) -> tuple[float, float]:
        point = load.points[index]
        if load.mode == "absolute_pq":
            return point
        if load.mode == "multiplier":
            p, q = self._baseline[native]
            return float(point) * p, float(point) * q
        p, pf = point
        q = math.copysign(p * math.sqrt(1 - pf * pf) / abs(pf), pf)
        return p, q

    def apply(self, index: int) -> dict[str, Any]:
        if not isinstance(index, int) or index < 0 or index >= self.spec.sample_count:
            raise ExogenousApplicationError(f"A05I2_REQUIRED_SAMPLE_UNAVAILABLE: index={index}")
        # Prepare every property before any native write. No hidden state repair.
        operations: list[tuple[str, str, float]] = []
        for profile in self.spec.loads:
            for raw in profile.targets:
                native = self._names[raw.casefold()]
                p, q = self._pair(profile, native, index)
                if not math.isfinite(p) or not math.isfinite(q):
                    raise ExogenousApplicationError(f"Nonfinite derived load demand: {native}")
                operations.extend(((native, "kW", p), (native, "kvar", q)))
        for profile in self.spec.pvs:
            for raw in profile.targets:
                native = self._names[raw.casefold()]
                g = profile.irradiance_kw_m2[index]
                if profile.outdoor_temperature_c is None:
                    temperature = 25.0
                    mode = "constant_25C"
                else:
                    temperature = profile.outdoor_temperature_c[index] + 1000.0 * g / (
                        profile.u0 + profile.u1 * profile.wind_speed_m_s[index]
                    )
                    mode = "faiman"
                if not math.isfinite(temperature):
                    raise ExogenousApplicationError(f"Nonfinite PV temperature: {native}")
                operations.extend(((native, "Irradiance", g), (native, "Temperature", temperature)))
        receipts = []
        try:
            for native, prop, value in operations:
                self._access.backend.write_object_property(native, prop, value)
            for profile in self.spec.loads:
                for raw in profile.targets:
                    native = self._names[raw.casefold()]
                    expected = self._pair(profile, native, index)
                    values = self._access.backend.read_object_properties(native, ("kW", "kvar"))
                    keyed = {k.casefold(): v for k, v in values.items()}
                    actual = (float(keyed["kw"]), float(keyed["kvar"]))
                    if not all(math.isclose(x, y, rel_tol=1e-6, abs_tol=1e-5) for x, y in zip(actual, expected)):
                        raise ExogenousApplicationError(f"Native load P/Q readback mismatch: {native}")
                    receipts.append({"native_entity": native, "kind": "load", "mode": profile.mode,
                                     "specified_kw_kvar": list(expected), "native_kw_kvar": list(actual)})
            for profile in self.spec.pvs:
                for raw in profile.targets:
                    native = self._names[raw.casefold()]
                    values = self._access.backend.read_object_properties(native, ("Irradiance", "Temperature"))
                    keyed = {k.casefold(): v for k, v in values.items()}
                    actual_g, actual_t = float(keyed["irradiance"]), float(keyed["temperature"])
                    expected_g = profile.irradiance_kw_m2[index]
                    expected_t = (25.0 if profile.outdoor_temperature_c is None else
                                  profile.outdoor_temperature_c[index] + 1000.0 * expected_g /
                                  (profile.u0 + profile.u1 * profile.wind_speed_m_s[index]))
                    if not (math.isclose(actual_g, expected_g, rel_tol=1e-6, abs_tol=1e-6)
                            and math.isclose(actual_t, expected_t, rel_tol=1e-6, abs_tol=1e-5)):
                        raise ExogenousApplicationError(f"Native PV irradiance/temperature readback mismatch: {native}")
                    receipts.append({"native_entity": native, "kind": "pv", "irradiance_kw_m2": actual_g,
                                     "temperature_c": actual_t,
                                     "temperature_source": "constant_25C" if profile.outdoor_temperature_c is None else "faiman",
                                     "u0": profile.u0, "u1": profile.u1,
                                     "coefficient_source": "generic_faiman_default" if (profile.u0, profile.u1) == (25.0, 6.84) else "user_configured"})
        except Exception as exc:
            raise ExogenousApplicationError("A05I2_NATIVE_APPLICATION_OR_READBACK_FAILED") from exc
        return {"source_id": self.spec.source_id, "source_sha256": self.spec.source_sha256,
                "sample_index": index, "sample_count": self.spec.sample_count,
                "pv_temperature_extension": A05_PV_TEMPERATURE_EXTENSION if self._temperature_extension else None,
                "pv_temperature_extension_sha256": A05_PV_TEMPERATURE_EXTENSION_SHA256 if self._temperature_extension else None,
                "bindings": tuple(receipts)}

    def capture_realized(self, receipt: dict[str, Any]) -> None:
        """Record electrical terminal complex powers separately after solve.

        These are NOT the native nominal kW/kvar load setpoints or PV ratings.
        No additional solve and no public/controller truth disclosure occurs.
        """
        try:
            for entry in receipt["bindings"]:
                full = entry["native_entity"]
                powers = self._access.backend.read_runtime_channel("CircuitElement", full, "terminal_power")
                if not isinstance(powers, (tuple, list)) or not powers:
                    raise ValueError("No terminal power data")
                values = tuple(complex(x) for x in powers)
                if any(not math.isfinite(p.real) or not math.isfinite(p.imag) for p in values):
                    raise ValueError("Nonfinite terminal power")
                entry["terminal_powers_kw_kvar"] = tuple((float(p.real), float(p.imag)) for p in values)
        except Exception as exc:
            raise ExogenousApplicationError("A05I2_REALIZED_TERMINAL_POWER_READ_FAILED") from exc

    def public_provenance(self, index: int) -> dict[str, Any]:
        return {"status": "APPLIED", "source_sha256": self.spec.source_sha256,
                "sample_index": index, "temperature_extension_version":
                A05_PV_TEMPERATURE_EXTENSION if self._temperature_extension else None,
                "temperature_extension_sha256":
                A05_PV_TEMPERATURE_EXTENSION_SHA256 if self._temperature_extension else None}
