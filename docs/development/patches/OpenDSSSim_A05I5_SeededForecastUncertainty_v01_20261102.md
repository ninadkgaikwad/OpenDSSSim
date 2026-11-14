# A05I5 Seeded, Forecast-Only Gaussian Errors — Implementation V01

This amendment is derived from the accepted A05I4 233-file qualified baseline and the ratified 2026-10-27 A05.5 contract. This is a **runtime qualification candidate** until independently verified on the installed AltDSS environment. A03/A04, all feeders, A05I1–I4 physical replay, the R02A backend and `ProblemSpec`/Gym schemas are unchanged.

## Public interface

```python
from opendsssim.environment import ForecastNoiseSpec, GaussianScale, OpenDSSSimulator

noise = ForecastNoiseSpec(
    mode="additive_gaussian", seed=731,
    boundary="truncate",  # default; explicit alternative: "clip"
    scales=(
        GaussianScale("load.kw", "Load.S1a", sigma=2.0),
        GaussianScale("load.kvar", "Load.S1a", sigma=(1.0, 2.0, 3.0)),
        # optional linear rule: sigma0=0.5, alpha=0.2
    ),
)
env = OpenDSSSimulator(network, exogenous_replay=replay, forecast_noise=noise)
observation, info = env.reset(seed=100)
forecast = env.exogenous_forecast(2)
```

`forecast_noise=None` or `ForecastNoiseSpec()` retains A05I4's unmodified perfect-exogenous oracle. `additive_gaussian` requires an explicit integer seed and exact channel/entity sigma contracts. Constant, finite per-lead and `sigma0+alpha*lead` rules are supported, without implied percentages. Missing required primitive scales, mismatched declared channels, invalid sigma or lead coverage fail closed. The explicit `seed` is combined with `reset(seed=...)` and the episode identity, source/binding SHA, channel/entity, logical issue index and lead. It never consumes a mutable/global PRNG. Source tiling does not repeat forecast errors for different logical issues.

Each primitive is sampled from a Gaussian with the specified sigma and conditioned on its qualified domain using a deterministic bounded inverse-CDF transform. `boundary="clip"` is **opt-in** and emits immutable private receipts recording unperturbed, raw, clipped and accepted values; raw truth/uncertainty draws are not exposed in `exogenous_forecast()`, Gym, or step info. Strong tail configurations with numerically unresolved truncated-Gaussian probability are rejected rather than silently clamped or retried indefinitely. Sampling algorithm: `A05I5.gaussian.v1.sha256-53bit-inverse-cdf`.

- `load.kw` and `load.multiplier` follow the nonnegative domain of the current A05I2 typed physical source; `load.kvar` is signed. No global absolute-power constraint is inferred for other future typed sources.
- `load.signed_pf` preserves the qualified nonzero PF sign, with magnitude (0,1]. When P/PF is the declared mode, `load.kvar` is **derived** consistently; it has no independent Gaussian sigma.
- PV irradiance and wind are nonnegative. Weather-driven cell temperature is **derived** from perturbed irradiance, ambient and wind with the qualified Faiman coefficients; otherwise, the qualified fallback remains 25 °C. Derived cell temperature has no independent Gaussian sigma.
- For multiplier-mode loads, forecasts return the declared multiplier in pu; native baseline P/Q are not disclosed through the read-only forecast. Physical P/Q remain correctly computed by A05I2 during snapshots.

`ForecastResult` and `ForecastValue` keep their frozen read-only structure with added optional noise annotations (`noise_mode`, config hash, sigma, boundary/clip flag). `ForecastNoiseEngine.transform()` also produces **trusted, internal** `TrustedPrimitiveAudit` records of primitive pre/post values for testing and qualified engineering routes. `OpenDSSSimulator._forecast_private_audit` retains only the last request's private audit. No extra controller-readable truth, arbitrary forecast providers, scenario axes, reward/action modifications, history tier, Snapshot solve or native write are introduced. Durable trusted-audit persistence and A05.6 controller-information integration remain A05I6 work.

## Qualification boundary

Targeted A05I5 unit/real IEEE-123 tests, A05I4–I1 and R02A regressions plus three fresh-process full `tests` regressions must pass with no skips and no `JSONDecodeError`. Check zero forecast-native writes/solves, reset/step physical-source parity, strict/tile coverage, deterministic call-order invariance, multiple source/group alignment and protected raw audit. Exact manifest verification before/after is mandatory. R01 native Windows traces and R02 mitigation status remain OPEN.
