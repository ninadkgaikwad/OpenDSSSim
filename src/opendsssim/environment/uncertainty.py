"""A05I5 deterministic, forecast-only additive Gaussian benchmark.

The oracle is the sole future exogenous source. This module never imports an
AltDSS backend, accesses a Plant, advances a clock, or uses a global PRNG.
The explicit private audit is *not* part of the controller forecast payload.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from hashlib import sha256
import json
import math
from statistics import NormalDist
from typing import Any

from .forecast import (ForecastResult, ForecastValue, ForecastError,
                       ForecastSelectionError, _selector)
from .exogenous import ExogenousProfileSpec
from .replay import ReplaySpec


class ForecastNoiseError(ForecastError):
    """Invalid uncertainty configuration or numerically inadmissible draw."""


class ForecastNoiseCoverageError(ForecastNoiseError):
    """A configured lead has no explicit forecast-error scale."""


def _finite_nonnegative(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ForecastNoiseError(f"{label} must be a finite nonnegative numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ForecastNoiseError(f"{label} must be finite and nonnegative")
    return number


@dataclass(frozen=True, slots=True)
class GaussianScale:
    """One exact primitive channel/entity and one explicit sigma rule.

    ``sigma`` is a constant or a tuple of per-lead values. Alternatively,
    provide BOTH ``sigma0`` and ``alpha`` for sigma0 + alpha*lead.
    """
    channel_id: str
    entity_id: str
    sigma: float | tuple[float, ...] | None = None
    sigma0: float | None = None
    alpha: float | None = None

    def __post_init__(self) -> None:
        if (not isinstance(self.channel_id, str) or not self.channel_id.strip() or
                not isinstance(self.entity_id, str) or not self.entity_id.strip()):
            raise ForecastNoiseError("Exact nonempty channel/entity names are required")
        if self.sigma is not None:
            if self.sigma0 is not None or self.alpha is not None:
                raise ForecastNoiseError("Use either sigma or sigma0+alpha, never both")
            if isinstance(self.sigma, (tuple, list)):
                if not self.sigma:
                    raise ForecastNoiseError("Per-lead sigma must not be empty")
                object.__setattr__(self, "sigma", tuple(
                    _finite_nonnegative(x, "lead sigma") for x in self.sigma
                ))
            else:
                object.__setattr__(self, "sigma", _finite_nonnegative(self.sigma, "sigma"))
        else:
            if self.sigma0 is None or self.alpha is None:
                raise ForecastNoiseError("Specify a sigma or both sigma0 and alpha")
            object.__setattr__(self, "sigma0", _finite_nonnegative(self.sigma0, "sigma0"))
            object.__setattr__(self, "alpha", _finite_nonnegative(self.alpha, "alpha"))

    def at(self, lead: int) -> float:
        if self.sigma is not None:
            if isinstance(self.sigma, tuple):
                if lead >= len(self.sigma):
                    raise ForecastNoiseCoverageError(
                        f"Sigma vector insufficient for lead {lead}, {self.channel_id}/{self.entity_id}"
                    )
                return self.sigma[lead]
            return self.sigma
        assert self.sigma0 is not None and self.alpha is not None
        return _finite_nonnegative(self.sigma0 + self.alpha * lead, "lead-dependent sigma")


@dataclass(frozen=True, slots=True)
class ForecastNoiseSpec:
    """V1 has one synthetic future-truth-based realization, no ensembles."""
    mode: str = "none"
    seed: int | None = None
    boundary: str = "truncate"
    scales: tuple[GaussianScale, ...] = ()
    identity_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        if self.mode not in {"none", "additive_gaussian"}:
            raise ForecastNoiseError("A05I5 modes: none or additive_gaussian only")
        if self.boundary not in {"truncate", "clip"}:
            raise ForecastNoiseError("A05I5 boundary: truncate (default) or explicit clip")
        if self.seed is not None and (isinstance(self.seed, bool) or not isinstance(self.seed, int)):
            raise ForecastNoiseError("Experiment seed must be an integer")
        if not isinstance(self.scales, (tuple, list)) or any(
            not isinstance(x, GaussianScale) for x in self.scales
        ):
            raise ForecastNoiseError("scales must contain only typed GaussianScale records")
        object.__setattr__(self, "scales", tuple(self.scales))
        keys = [(x.channel_id.casefold(), x.entity_id.casefold()) for x in self.scales]
        if len(keys) != len(set(keys)):
            raise ForecastNoiseError("Repeated channel/entity sigma configuration")
        if self.mode == "none":
            if self.scales or self.boundary != "truncate":
                raise ForecastNoiseError("none mode may not specify active Gaussian options")
        elif self.seed is None or not self.scales:
            raise ForecastNoiseError("additive_gaussian requires explicit seed and sigma scales")
        normalized = {
            "version": "A05I5.gaussian.v1.sha256-53bit-inverse-cdf",
            "mode": self.mode, "seed": self.seed, "boundary": self.boundary,
            "scales": [{"channel": x.channel_id.casefold(), "entity": x.entity_id.casefold(),
                        "sigma": x.sigma, "sigma0": x.sigma0, "alpha": x.alpha}
                       for x in sorted(self.scales,
                                       key=lambda y: (y.channel_id.casefold(), y.entity_id.casefold()))],
        }
        object.__setattr__(self, "identity_sha256", sha256(
            json.dumps(normalized, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest().upper())


@dataclass(frozen=True, slots=True)
class TrustedPrimitiveAudit:
    """Never place these raw/truth fields in Gym, info or public forecast."""
    episode_id: str
    decision_index: int
    lead_index: int
    source_sha256: str
    channel_id: str
    entity_id: str
    sigma: float
    unperturbed_value: float
    raw_gaussian_value: float
    accepted_value: float
    boundary: str
    was_clipped: bool
    substream_sha256: str


_NORMAL = NormalDist()
_SAMPLER_VERSION = "A05I5.gaussian.v1.sha256-53bit-inverse-cdf"
_PRIMITIVE_CHANNELS = frozenset({
    "load.kw", "load.kvar", "load.signed_pf", "load.multiplier",
    "pv.irradiance", "pv.outdoor_temperature", "pv.wind_speed",
})


def _stable_uniform(key: dict[str, Any]) -> tuple[float, str]:
    digest = sha256(json.dumps(key, sort_keys=True, separators=(",", ":"),
                               allow_nan=False).encode()).digest()
    bits = int.from_bytes(digest[:8], "big") >> 11  # 53 unbiased bits
    return (bits + 0.5) / (1 << 53), digest.hex().upper()


def _bounds(channel: str, truth: float) -> tuple[float, float]:
    if channel in {"load.kw", "load.multiplier", "pv.irradiance", "pv.wind_speed"}:
        return 0.0, math.inf
    if channel == "load.signed_pf":
        # Preserve the qualified native signed-PF sign, and avoid PF=0.
        # There is no fabricated minimum *positive* PF configuration.
        return ((0.0, 1.0) if truth > 0 else (-1.0, 0.0))
    return -math.inf, math.inf


def _sample_gaussian(mu: float, sigma: float, u: float,
                     lower: float, upper: float, boundary: str) -> tuple[float, float, bool]:
    if sigma == 0:
        return mu, mu, False
    raw = mu + sigma * _NORMAL.inv_cdf(u)
    if not math.isfinite(raw):
        raise ForecastNoiseError("Nonfinite raw Gaussian draw")
    if boundary == "clip":
        accepted = min(max(raw, lower), upper)
        if accepted == 0 and lower == 0 and upper == 1:
            accepted = math.nextafter(0.0, 1.0)
        elif accepted == 0 and lower == -1 and upper == 0:
            accepted = math.nextafter(0.0, -1.0)
        return raw, accepted, raw != accepted
    # Inverse-CDF conditional Gaussian, no rejection loops or implicit clipping.
    cdf_lo = 0.0 if lower == -math.inf else _NORMAL.cdf((lower - mu)/sigma)
    cdf_hi = 1.0 if upper == math.inf else _NORMAL.cdf((upper - mu)/sigma)
    mass = cdf_hi - cdf_lo
    if mass <= 1e-14 or not math.isfinite(mass):
        raise ForecastNoiseError("Truncated Gaussian has numerically unresolved feasible mass")
    probability = cdf_lo + mass * u
    if not 0.0 < probability < 1.0:
        raise ForecastNoiseError("Truncated Gaussian probability lost numerical resolution")
    accepted = mu + sigma * _NORMAL.inv_cdf(probability)
    if not math.isfinite(accepted) or not lower <= accepted <= upper:
        raise ForecastNoiseError("Truncated Gaussian accepted draw is outside physical domain")
    if accepted == 0 and (lower == 0 and upper == 1 or lower == -1 and upper == 0):
        raise ForecastNoiseError("Truncated signed PF resolved numerically to zero")
    return raw, accepted, False


class ForecastNoiseEngine:
    """Pure projection of one A05I4 oracle into one seeded noisy trajectory."""

    def __init__(self, spec: ForecastNoiseSpec, *, replay_spec: ReplaySpec | None = None,
                 explicit_source: ExogenousProfileSpec | None = None,
                 reset_seed: int | None = None):
        if not isinstance(spec, ForecastNoiseSpec):
            raise ForecastNoiseError("ForecastNoiseSpec required")
        self.spec = spec
        self.replay_spec = replay_spec
        self.explicit_source = explicit_source
        self.reset_seed = reset_seed
        self._scales = {(x.channel_id.casefold(), x.entity_id.casefold()): x
                        for x in spec.scales}

    def _pv_coefficients(self, entity_id: str) -> tuple[float, float]:
        if self.replay_spec is not None:
            matches = [b for b in self.replay_spec.bindings if b.kind == "pv" and
                       entity_id.casefold() in {x.casefold() for x in b.targets}]
            if len(matches) != 1:
                raise ForecastNoiseError("PV forecast binding must be unique")
            return matches[0].u0, matches[0].u1
        if self.explicit_source is not None:
            matches = [p for p in self.explicit_source.pvs if
                       entity_id.casefold() in {x.casefold() for x in p.targets}]
            if len(matches) != 1:
                raise ForecastNoiseError("Explicit PV forecast binding must be unique")
            return matches[0].u0, matches[0].u1
        raise ForecastNoiseError("Missing qualified PV binding")

    def validate_declared(self, result: ForecastResult) -> None:
        available = {(v.channel_id.casefold(), v.entity_id.casefold())
                     for v in result.values if v.channel_id in _PRIMITIVE_CHANNELS}
        illegal = set(self._scales) - available
        if illegal:
            raise ForecastNoiseError("Sigma configured for undeclared/derived source: " + str(sorted(illegal)))

    def transform(self, oracle: ForecastResult, *, channel_ids=None,
                  entity_ids=None) -> tuple[ForecastResult, tuple[TrustedPrimitiveAudit, ...]]:
        if self.spec.mode == "none" or oracle.status != "AVAILABLE":
            return oracle, ()
        channels = _selector(channel_ids, "channel_ids")
        entities = _selector(entity_ids, "entity_ids")
        available_channels = {v.channel_id.casefold() for v in oracle.values}
        available_entities = {v.entity_id.casefold() for v in oracle.values}
        if channels is not None and set(channels) - available_channels:
            raise ForecastSelectionError("A05I5 requested channel unavailable")
        if entities is not None and set(entities) - available_entities:
            raise ForecastSelectionError("A05I5 requested entity unavailable")
        selected_entities = set(entities) if entities is not None else available_entities
        by_group: dict[tuple[int, str], dict[str, ForecastValue]] = {}
        for value in oracle.values:
            if value.entity_id.casefold() not in selected_entities:
                continue
            group = by_group.setdefault((value.lead_index, value.entity_id.casefold()), {})
            if value.channel_id in group:
                raise ForecastNoiseError("Ambiguous repeated qualified physical channel")
            group[value.channel_id] = value
        outputs: list[ForecastValue] = []
        audit: list[TrustedPrimitiveAudit] = []
        for (lead, _), group in by_group.items():
            wanted = set(group) if channels is None else {x for x in group if x.casefold() in channels}
            if not wanted:
                continue
            all_channels = set(group)
            if "load.multiplier" in group:
                primitive = {"load.multiplier"} & wanted
                derived: set[str] = set()
            elif "load.signed_pf" in group:
                primitive = ({"load.kw", "load.signed_pf"} if "load.kvar" in wanted else
                             {"load.kw", "load.signed_pf"} & wanted)
                derived = {"load.kvar"}
            elif "load.kw" in group:
                primitive = {"load.kw", "load.kvar"} & wanted
                derived = set()
            elif "pv.irradiance" in group:
                primitive = ({"pv.irradiance", "pv.outdoor_temperature", "pv.wind_speed"}
                             if "pv.cell_temperature" in wanted and "pv.outdoor_temperature" in group else
                             {"pv.irradiance", "pv.outdoor_temperature", "pv.wind_speed"} & wanted)
                derived = {"pv.cell_temperature"}
            else:
                raise ForecastNoiseError("Unknown qualified group of primitive channels")
            if any(x not in all_channels for x in primitive):
                raise ForecastNoiseError("Qualified physical primitives missing from oracle")
            calculated: dict[str, float] = {x: float(v.value) for x, v in group.items()}
            annotations: dict[str, tuple[float, bool]] = {}
            for channel in sorted(primitive):
                v = group[channel]
                scale = self._scales.get((channel.casefold(), v.entity_id.casefold()))
                if scale is None:
                    raise ForecastNoiseCoverageError(
                        f"Missing required sigma for {channel}/{v.entity_id}"
                    )
                sigma = scale.at(lead)
                lower, upper = _bounds(channel, float(v.value))
                key = {"version": _SAMPLER_VERSION, "configuration": self.spec.identity_sha256,
                       "seed": self.spec.seed, "reset_seed": self.reset_seed,
                       "episode": v.episode_id, "source_id": v.source_id,
                       "source_sha256": v.source_sha256, "binding_id": v.binding_id,
                       "channel": v.channel_id, "entity": v.entity_id,
                       "decision": v.decision_index, "lead": v.lead_index}
                u, digest = _stable_uniform(key)
                raw, accepted, clipped = _sample_gaussian(
                    float(v.value), sigma, u, lower, upper, self.spec.boundary)
                if channel == "load.signed_pf" and (accepted == 0 or abs(accepted) > 1):
                    raise ForecastNoiseError("Forecast signed PF out of physical domain")
                if not math.isfinite(accepted):
                    raise ForecastNoiseError("Non-finite conditioned forecast")
                calculated[channel] = accepted
                annotations[channel] = (sigma, clipped)
                audit.append(TrustedPrimitiveAudit(v.episode_id, v.decision_index,
                    lead, v.source_sha256, channel, v.entity_id, sigma, float(v.value),
                    raw, accepted, self.spec.boundary, clipped, digest))
            if "load.kvar" in derived:
                p, pf = calculated["load.kw"], calculated["load.signed_pf"]
                q = math.copysign(p * math.sqrt(max(0.0, 1-pf*pf)) / abs(pf), pf)
                if not math.isfinite(q):
                    raise ForecastNoiseError("Nonfinite derived load kvar")
                calculated["load.kvar"] = q
            if "pv.cell_temperature" in derived:
                if "pv.outdoor_temperature" not in group:
                    calculated["pv.cell_temperature"] = 25.0
                else:
                    u0,u1 = self._pv_coefficients(next(iter(group.values())).entity_id)
                    denom = u0 + u1 * calculated["pv.wind_speed"]
                    if denom <= 0:
                        raise ForecastNoiseError("Nonpositive Faiman denominator")
                    cell = calculated["pv.outdoor_temperature"] + 1000 * calculated["pv.irradiance"]/denom
                    if not math.isfinite(cell):
                        raise ForecastNoiseError("Nonfinite derived PV cell temperature")
                    calculated["pv.cell_temperature"] = cell
            for channel, v in group.items():
                if channel not in wanted:
                    continue
                sigma, clipped = annotations.get(channel, (None, False))
                outputs.append(replace(v, value=calculated[channel],
                    forecast_mode="synthetic_additive_gaussian",
                    noise_sigma=sigma, boundary_policy=self.spec.boundary if sigma is not None else None,
                    was_clipped=clipped))
        if not outputs:
            raise ForecastSelectionError("No qualified forecast channels selected")
        # Explicitly configured zero sigma is scientifically a perfect oracle,
        # even if the experiment selected the additive_gaussian configuration.
        scientific_mode = ("oracle_perfect_exogenous" if all(a.sigma == 0 for a in audit)
                           else "synthetic_additive_gaussian")
        outputs = [replace(v, forecast_mode=scientific_mode) for v in outputs]
        return replace(oracle, values=tuple(outputs),
                       forecast_mode=scientific_mode,
                       noise_mode="additive_gaussian",
                       noise_config_sha256=self.spec.identity_sha256), tuple(audit)
