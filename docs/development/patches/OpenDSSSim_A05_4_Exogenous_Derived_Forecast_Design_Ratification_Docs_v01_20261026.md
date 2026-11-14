# OpenDSSSim A05.4 - Exogenous-Derived Forecast Design Ratification, Docs-Only Patch

**Ratified:** 2026-10-26 (America/Los_Angeles)  
**Change type:** Two additive Markdown documentation files; no executable source, environment, dependencies, engine settings or feeder changes.  
**Exact predecessor:** A05.3 qualified 201-source-file manifest, SHA256 `64F71254F9A7241081AFB0DD381F6F110F6C1F13159E8EB9400F49509B65468D`.

## Ratification record

| Point | Disposition |
| --- | --- |
| 4.1 Forecast-vs-truth service boundary | Approved as proposed. Forecast readout does not mutate Plant or solve AltDSS. |
| 4.2 Forecast basis | **Amended:** exclusively the same CSV/Parquet or other explicitly defined exogenous channels ratified under A05.2. No separate callable/precomputed forecast providers and no persistence provider. Actual exogenous values reach Plant; optional forecast error affects only controller-facing predictions. |
| 4.3 Horizon/timing | Approved. `H > 0`, lead `ell = 0..H-1`, issued at `t[k]` and valid for `[t[k+ell],t[k+ell+1])`; A05.1 Option-A electrical sample and next decision times remain distinct. |
| 4.4 Channels/mapping | Approved. Use only qualified declared load/PV/weather/other exogenous bindings and physical-unit semantics. |
| 4.5 Scenario/uncertainty metadata | Approved. Actual forecast error generation, distribution, correlation and seeds are A05.5. |
| 4.6 Missingness/coverage | **Amended:** follow A05.2/A05.3 exogenous validation, resampling and replay exactly; default tile, optional strict, no new forecast-specific persistence/fallback policy. |
| 4.7 Fair information | Approved, with explicit scientific labeling: a zero-error future-truth-derived forecast is oracle/perfect-exogenous-forecast; a noisy one is a controlled synthetic forecast-error experiment, not automatically an operationally causal forecast. A05.6 governs disclosure and parity. |
| 4.8 Evidence and qualification | Approved: explicit origin/issue/lead/source/noise provenance, read-only calls, failure tests, old contract regressions and new manifest. |

## Physical and informational separation

Let `d[j]` denote the validated exogenous input applied to AltDSS for interval `j`. For controller decision `k`, lead `ell` and optional forecast member `s`:

`forecast[k,ell,s] = forecast_error_A05_5(d[k+ell], issue=k, lead=ell, scenario=s)`.

- `d[j]` is the user-declared source after A05.2/A05.3 mapping and replay; it is not regenerated independently for controller forecasting.
- The forecast error operator is explicitly the identity when disabled. Forecast-only error does not change the Plant input.
- A05.3 `tile`/`strict` and original source-time provenance apply at each target index `k+ell`.
- Forecast issue and valid times do not erase the fact that the baseline accesses future exogenous truth. This design is a **synthetic benchmark contract** and must be reported as such.

## A05.4 installation and next-stage gate

The package is intentionally documentation-only and installs exactly:

1. `docs/development/stages/A05_temporal_exogenous_integration/04_A05_4_Exogenous_Derived_Forecast_Contract_RATIFIED_20261026.md`.
2. `docs/development/patches/OpenDSSSim_A05_4_Exogenous_Derived_Forecast_Design_Ratification_Docs_v01_20261026.md` (this record).

The installer checks every qualified 201-file predecessor byte/hash, refuses all target overwrites, writes only those Markdown files, validates both, and emits a qualified **203-file** manifest and receipt into Downloads. A separate optional recovery script safely relocates only untouched A05.4 documents. Runtime implementation remains expressly unqualified.

Following this docs-only step, three A05 ratification blocks remain before the implementation gate: **A05.5 Forecast Error/Uncertainty**, **A05.6 Controller Information Boundary**, and **A05.7 Events/End-to-End Qualification**. These are *design gates*, distinct from subsequent implementation and validation milestones.

See the stage's A05.4 ratified contract for precise equations, source mapping, replay conditions, and directed runtime tests.
