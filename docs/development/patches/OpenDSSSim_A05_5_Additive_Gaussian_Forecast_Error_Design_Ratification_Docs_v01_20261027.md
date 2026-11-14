# OpenDSSSim A05.5 - Forecast Error and Seeded Replay, Docs-Only Ratification Patch

**Ratified:** 2026-10-27 (America/Los_Angeles)  
**Change type:** Exactly two new Markdown files; **no executable source, environment, feeder or controller mutation**.  
**Exact predecessor:** A05.4 documentation-only successor, **203 source files**, manifest SHA256 `09CF8BF9C8AEF525995842CA2D18F10C016910CF00E9AE855243DEC3A41A39A3`.

## Ratification record

| Item | Final user-approved decision |
| --- | --- |
| 5.1 Truth and forecast | Approved: authoritative A05.2/A05.3 exogenous truth feeds Plant; **no V1 plant-truth noise**; forecast errors affect controller predictions only. |
| 5.2 Distribution | **Amended:** `none` and **additive Gaussian/normal only**. No multiplicative/uniform/custom-noise providers. |
| 5.3 Magnitude | Approved for additive errors only. Sigma is in each channel's native physical unit and may be constant or lead-dependent; default zero. |
| 5.4 Physical validity | Approved: default physically domain-restricted Gaussian draw; optional explicit and auditable clipping; recalculate dependent Load/PF and Faiman PV signals consistently. |
| 5.5 Seeds | Approved: stable deterministic seed/substream identity; same requests yield the same results independent of call order and source tiling. |
| 5.6 Scenarios | **Amended:** **one** seeded forecast trajectory in V1; no scenario ensemble, covariance/correlation models, branching, quantiles or scenario weights. |
| 5.7 Controller parity | Approved: same physical truth and authorized noisy-forecast realization for RBC/MPC/RL within a problem; no hidden controller-specific noise. |
| 5.8 Evidence | Approved: fail-closed inputs, exact provenance, physical-bound treatment, no extra AltDSS writes/solves, deterministic replay and predecessor regressions. |

## Simplified V1 mathematics

For primitive qualified exogenous channel `c` and entity `e`, decision `k`, lead `ell`, and one episode seed `s`:

`d_hat[c,e,k+ell | k;s] = d[c,e,k+ell] + epsilon[c,e,k,ell;s]`,

where `epsilon=0` under `none`, or is generated from the configured zero-centered additive Gaussian before any required physical-domain restriction, with finite nonnegative `sigma[c,e,ell]`. The physical Plant receives the untouched `d[c,e,j]`. Dependent quantities are recomputed using the same A05.2 source transformations rather than given inconsistent separate errors.

**Scientific label:** `none` is **oracle/perfect-exogenous forecast** under A05.4's future-truth source basis. Additive Gaussian versions are **synthetic forecast-error benchmarks**, not automatically operational causal forecasts.

## Installation and next stage

The package installs exactly these documents:

1. `docs/development/stages/A05_temporal_exogenous_integration/05_A05_5_Additive_Gaussian_Forecast_Error_RATIFIED_20261027.md`.
2. `docs/development/patches/OpenDSSSim_A05_5_Additive_Gaussian_Forecast_Error_Design_Ratification_Docs_v01_20261027.md` (this document).

An exact 203-row A05.4 predecessor manifest/hashes guard the installer and validation. Targets cannot be overwritten. Successful qualification emits a new **205-file** successor manifest plus a JSON receipt in Downloads. An opt-in recoverable rollback moves only the two untouched new Markdown files.

A05.5 is **design documentation only**. After it, A05.6 controller information/visibility and A05.7 events/whole-stage qualification design are the two remaining ratification blocks before implementation planning. No science runs or AltDSS A05 source modifications are authorized by this package.
