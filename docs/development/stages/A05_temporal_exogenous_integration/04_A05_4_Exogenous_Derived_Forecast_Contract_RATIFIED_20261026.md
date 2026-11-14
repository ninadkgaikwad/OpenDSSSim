# A05.4 - Exogenous-Derived Controller Forecast Contract

**Ratified:** 2026-10-26 (America/Los_Angeles)  
**Status:** DESIGN RATIFIED; DOCUMENTATION ONLY; A05 RUNTIME NOT IMPLEMENTED OR QUALIFIED  
**Qualified predecessor:** A05.3 documentation-only successor, 201 files  
**Predecessor source-manifest SHA256:** `64F71254F9A7241081AFB0DD381F6F110F6C1F13159E8EB9400F49509B65468D`

## 1. Purpose and preserved boundaries (4.1)

A05.4 defines a **separate, read-only controller forecast view** of the **same user-supplied or user-declared exogenous signals** defined and physically bound under A05.2 and indexed/replayed under A05.3. The realized values go to the Plant; forecasts presented to controllers may have optional, qualified forecast perturbations. Forecast retrieval cannot write AltDSS, advance the A05.1 UTC clock, invoke a power-flow solve, alter realized truth, or create a controller action. Preserve frozen A03/A04 Plant != Problem != Controller, the exact A04 authority/space contracts, and A05.1 Option-A reset/step timing.

## 2. Exactly one forecast-generation basis (4.2; user amendment)

**The sole A05.4 forecast basis is A05.2/A05.3 exogenous input.** Each eligible forecast channel comes from the actual user-supplied CSV/Parquet physical input or another explicitly declared exogenous source/definition already accepted by A05.2 (for example, a constant declared signal). All source-to-device mappings, units, validations, and physical transformations are inherited. A05.4 introduces **no separate callable forecast model, no standalone precomputed-forecast-provider schema, and no persistence provider**. A standalone model may belong to a future separately ratified stage, not to this frozen A05.4 contract.

Let `d[c,e,k]` be the actual A05.3-aligned physical exogenous sample for channel `c`, entity `e`, and interval `k`, after its approved source mapping. For a forecast requested at decision `k` and lead `ell`, the unperturbed basis is the **same qualified source** at the future logical index `k+ell`. A05.5 may subsequently apply an approved forecast-only error operator:

`d_hat[c,e,k+ell | k,s] = ForecastError_A05_5(d[c,e,k+ell], issue=k, lead=ell, channel=c, entity=e, scenario=s)`.

The operator is the identity when forecast noise is explicitly disabled. Plant input `d[c,e,j]` remains the A05.2/A05.3 truth for physical step `j`; a forecast-only perturbation never flows back into the Plant. The optional forecast error families, physical clipping/constraints, correlations, seeding and scenario construction are **deferred to A05.5**: A05.4 does not invent random draws or silently assume a noise distribution.

**Scientific labeling is essential:** using a future realized exogenous profile as an unperturbed prediction is perfect foresight of that exogenous channel, even though forecast issue-time metadata is well formed. Such a zero-error case must be identified as an **oracle/perfect-exogenous-forecast diagnostic** rather than called an operational forecast. Perturbed future-truth forecasts are a controlled *synthetic forecast-error benchmark*, not automatically deployable causal predictions. This is the user-selected experimental design and does not waive A05.6's information/fairness disclosures.

## 3. Clock, horizon and issue/target semantics (4.3)

Let `t[k] = t0 + k*dt`, where `dt > 0` is the episode's A05.3 interval in seconds (generic no-source default `3600 s`). A request has decision index `k`, a positive integer horizon `H`, and leads `ell = 0,...,H-1`, corresponding to logical target intervals `[t[k+ell], t[k+ell+1])`. The request's `issue_time` is the authorized decision time `t[k]`; a forecast version exposed for that decision is not issued later than `t[k]`.

The origin is **the next controller decision clock**, not the timestamp of the most recent electrical solve. Under ratified A05.1 Option A, `reset()` uses `d[0]`, and `step(action[0])` also solves with `d[0]` before advancing the next decision to `t[1]`. Consequently, after the first step a new forecast request anchored at `t[1]` targets `d[1],d[2],...`, even though the returned electrical observation was sampled at `t[0]`. Forecast calls do not increment the authoritative `N+1` solve count.

## 4. Eligible channels, mapping and tensor contract (4.4)

- Reuse exactly the A05.2 exogenous declarations and qualified bindings for available load P/Q or P+signed-PF, load multipliers, PV irradiance/availability and optional weather. Optional other declared physical exogenous channels can be forecast if registered under that same contract. Do not require forecasts of all conceivable channels.
- The conceptual typed record is indexed by `(issue_time_utc, decision_index, lead_index, valid_interval_start_utc, channel_id, entity_id[, scenario_id])`, with a finite value, declared physical unit, source identity, and optional A05.5 uncertainty fields. Shape and order must be explicit, stable and checked; never infer channel/entity order from filenames or array position.
- Derived forecasts use the same declared physical transformations as corresponding truth. For the A05.2 PV convention, forecast cell temperature can be derived consistently via the frozen Faiman-like formula from forecast irradiance, outside temperature and wind speed, with the ratified 25 degC fallback when the required weather pair is unavailable. The actual PV cell temperature uses actual plant-side sources. Do not write forecast PV temperature into AltDSS.
- No forecasts of bus voltages, power-flow states, actuator outcomes, or future topology are automatically generated by the exogenous-forecast service. Any such controller internal model or event disclosure requires separate contracts.

## 5. Deterministic base, uncertainty metadata and scenarios (4.5)

The source-aligned base is deterministic for a qualified episode configuration. Support a single point forecast when no A05.5 perturbation is enabled, and permit versioned scenario/member/quantile/dispersion metadata for later A05.5. An issue time and lead identify *which source sample and optional perturbation* produced a value, even when different rolling requests target the same physical interval. Seeds, error correlations across leads/channels, and sample reuse belong to A05.5, while the forecast result must carry their identities when applicable.

## 6. Required coverage, invalid inputs, replay and no invented fallback (4.6; user amendment)

**Inherit the exogenous policies as already ratified in A05.2/A05.3.** CSV/Parquet parsing, timezones/DST, sample cadence, alignment, declared interpolation/hold, malformed/nonfinite values, physical units, required/optional channels, source indices and provenance use the exact same rules. **Tile is the default** and reuses valid future logical samples by modular source index, with each original source time/cycle distinguished from the forecast's logical target time. **Strict is opt-in** and rejects a forecast whose required lead falls outside valid source coverage, without reading an invalid row or silently padding with a last value. No unapproved persistence, forecast-specific extrapolation, future file, fitted predictive model, or substituted perfect truth is invented.

If no qualified exogenous forecastable channel was declared, the service reports a typed **unavailable/not-configured** result. If a particular forecast request lacks required coverage, it returns/raises a typed, explicit forecast-coverage failure; it does not automatically terminate a physically valid plant episode or perform a solve. Controller requirements and how to handle an unavailable forecast must be declared at the future A05.6 controller information boundary. Physical truth still obeys its own A05.3 strict/tile limits; a longer requested forecast horizon must not fabricate a new `d[N]` requirement for ordinary plant stepping.

## 7. Controller information and fairness (4.7)

RBC, MPC and RL receive data only through the qualified controller-visible forecast interface and A05.6 observation permissions, not through the underlying truth-table/cache handle. One shared forecast configuration (including base exogenous profiles, horizon eligibility, forecast-error parameters and seed/scenario realization) applies for controlled comparisons within P1; separately, use a shared declared configuration within P2. Algorithms may elect not to use a permitted forecast, but cannot gain another controller's hidden future truth by bypassing the service.

**Important scientific qualification:** this user's chosen source-derived forecast scheme intentionally uses future truth as its base. Ordinary controller comparisons may use the same explicitly perturbed synthetic forecasts, but claims must distinguish them from operational causal forecasts; zero-noise results are labeled oracle/perfect-exogenous-forecast. A05.6 must expose the limitation in the permitted-information contract and reporting.

## 8. Provenance, safety, qualification and scope (4.8)

At minimum record: episode/source/content hashes, A05.2 binding identity, A05.3 time/UTC/dt/replay/index/cycle identities, issue and target times, decision index, horizon/lead, channel/entity, units, baseline source index, A05.5 error/seed/scenario identity when enabled, and availability/failure reason. Do not disclose private full future truth in a normal controller Gym observation or log visible to the controller. H0-H3 and FAST/STANDARD/AUDIT retain their existing physical and temporal semantics.

Directed runtime qualification before A05 implementation freeze:

1. Exact source/binding parity for load/PV/weather forecasts across CSV and Parquet, including declared constant sources and Faiman-derived PV temperature.
2. Correct rolling `H` leads and `t[k]` anchors around reset/first step; forecast requests cause no AltDSS writes/solves.
3. Shared physical source plus optional forecast-only perturbation; verify that forecast changes do not affect physical input or actual power flow.
4. Explicit oracle/zero-error scientific label; later A05.5 noisy-case repeatability and cross-controller scenario parity.
5. Strict/tile/default-tile forecast coverage, arbitrary horizon at episode tail, different source periods, invalid UTC/DST/units/nonfinite/missing rows and no implicit persistence.
6. A05.6 API restrictions and no alternate runtime forecast provider path; truth remains protected from controller bypass.
7. Full A04/A05.1/A05.2/A05.3 predecessor regression, 201-file predecessor hash guard, and complete successor source manifest.

**Final disposition:** A05.4.1-A05.4.8 DESIGN RATIFIED with the user's single-source exogenous-derived forecast basis and inherited exogenous coverage/fallback rules. **Documentation only** is authorized here, not A05 runtime implementation or science execution. The remaining design ratifications before the planned A05 implementation gate are A05.5, A05.6 and A05.7.
