# A05.5 - Additive Gaussian Forecast Error, Single Realization, and Reproducibility

**Ratified:** 2026-10-27 (America/Los_Angeles)  
**Status:** DESIGN RATIFIED; DOCUMENTATION ONLY; A05 RUNTIME NOT IMPLEMENTED OR QUALIFIED  
**Qualified predecessor:** A05.4 documentation successor, 203 files (**laptop PASS reported; full CSV not independently uploaded in this turn**)  
**Predecessor source-manifest SHA256:** `09CF8BF9C8AEF525995842CA2D18F10C016910CF00E9AE855243DEC3A41A39A3`

## 1. Contract and scope (5.1)

A05.5 freezes the **forecast-only** error transformation for A05.4's unique, exogenous-derived forecast basis. Every forecast derives from a qualified A05.2/A05.3 exogenous source (CSV/Parquet or another explicitly declared exogenous signal); no separate forecasting-model, precomputed forecast-file, or persistence provider is introduced. The unperturbed values remain the authoritative physical inputs to the Plant. **V1 adds no stochastic plant-truth perturbation.** Preserving A03/A04 Plant != Problem != Controller, A05.1 Option-A reset/step clock, A05.3 default tile/opt-in strict replay, and H0-H3 physical histories is mandatory.

For a primitive channel `c`, entity `e`, controller decision `k`, forecast lead `ell` in `0..H-1`, and one episode seed `s`, define the A05.3 qualified physical exogenous sample `d[c,e,k+ell]`. The controller-visible *primitive* forecast is:

`d_hat[c,e,k+ell | k;s] = d[c,e,k+ell] + epsilon[c,e,k,ell;s]`.

The plant still receives `d[c,e,j]` at physical interval `j`, never `d_hat`. A forecast read is non-mutating: it causes zero authoritative solves, physical writes, decisions, or clock advances. Forecast issue time is the logical decision time `t[k]`, **not** the timestamp of the most recent electrical sample, which can be `t[k-1]` after A05.1 Option-A `step()`.

## 2. Exactly two noise modes (5.2; user restriction)

V1 supports only:

1. `none`: `epsilon = 0` identically; forecast equals the future realized exogenous signal.
2. `additive_gaussian`: for an admissible primitive signal, an error drawn from a **zero-centered Gaussian before physical-domain conditioning**, `epsilon_raw ~ Normal(0, sigma[c,e,ell]^2)`, is added in that signal's declared physical units.

There are **no multiplicative, uniform, independently supplied forecast-model, scenario-family, or user-defined-noise callback modes in V1**. Sigma is finite and nonnegative; `sigma=0` is the exact identity. Default `mode=none` with no implicit or fabricated nonzero uncertainty. The exact mathematically defined physical-domain conditioning in Section 4 can change the mean of the *accepted* errors near bounds; do not misreport post-conditioning errors as guaranteed zero-mean Gaussian.

## 3. Noise magnitude across channels/entities/leads (5.3)

Noise standard deviation uses the **same unit as the primitive exogenous signal**, e.g., kW for active load, kvar for reactive load, W/m2 for irradiance, degC for air temperature and m/s for wind. Users may configure distinct nonnegative sigmas for each qualified channel/entity; no percentages are implicitly reinterpreted as absolute units.

- Default: `none`, equivalently `sigma=0`.
- With additive Gaussian explicitly enabled, a user-configured constant sigma may be shared by all leads of a channel/entity.
- Alternatively, an explicit finite nonnegative vector `[sigma_0,...,sigma_(H-1)]` may vary with forecast lead. An optional user-specified linear rule `sigma_ell = sigma_0 + alpha*ell` with `sigma_0 >= 0`, `alpha >= 0` is only syntactic convenience and is **not** a default growth law.
- All mappings and lead dimensions are validated against declared channels, entities and horizon. Missing configured values are errors for required forecasts, not silently filled with arbitrary numbers.

## 4. Physical bounds and consistent derived signals (5.4)

Apply additive errors to the **qualified primitive inputs** and then derive physically dependent forecast quantities using the same A05.2 transformations:

- For a load multiplier, perturb the declared multiplier and recompute associated P and Q using the qualified base demand. For a P + signed PF source, recompute Q consistently from the perturbed declared primitives, rather than assigning an unrelated Q perturbation. For directly declared independent P/Q channels, each may have its own configured additive error.
- Forecast PV cell temperature must be calculated from forecast irradiance, ambient temperature and wind speed using the approved Faiman-like relation; retain the ratified 25 degC fallback when the complete weather pair is unavailable. Do not independently add an unrelated cell-temperature error unless it is separately defined as a primitive qualified exogenous channel in a future revision.
- Validate channel-specific domains: nonnegative irradiance and wind speed, valid signed or unsigned load domains as declared, PF domain if applicable, and other registered physical bounds. Do not invent blanket positive-power rules for legitimately signed demand/export values.
- **Default** for Gaussian values crossing a physical boundary: sample according to the Gaussian distribution **restricted to the valid physical domain** (a truncated/conditional Gaussian under the transformed signal). A configuration whose feasible domain is empty fails preflight. Implementation must use deterministic, qualified finite procedures and cannot hang indefinitely retrying draws.
- **Optional explicit clipping** of an unconstrained draw is permitted only when selected in the run configuration; each clip and its pre-/post-bound values must be recorded. There is no hidden blanket clipping, NaN fill or default zero substitution.
- Physical-domain rules protect forecast validity; they must never alter the underlying realized plant exogenous data.

## 5. Seed-controlled deterministic single-realization replay (5.5)

One explicit experiment seed, together with stable identities `(episode, source identity, channel, entity, issue decision k, lead ell)`, defines the **one forecast-error realization** for each forecast record. Derive independent deterministic substreams from a versioned stable digest/canonical serialization, not Python's randomized `hash()` or mutable global RNG state. The exact algorithm and version must be in provenance and runtime qualification evidence.

Consequences:

1. Repeating a run with identical qualified inputs, seed and configuration reproduces the forecast values byte-for-byte or to a documented numerical tolerance.
2. Requesting the same forecast twice does not resample it; request order and execution profile do not alter results.
3. The same target interval may have different forecast-error realizations at different **issue** indices, since each is a distinct rolling forecast. All are deterministic for the seed.
4. A05.3 tiled source values retain source-row/cycle provenance, while forecast errors are keyed to the advancing *logical* issue/lead, not reused merely because a source row repeats.
5. `reset()` and `step(action[0])` preserve the ratified *same physical* `d[0]` realization; a new forecast noise draw is not an additional physical exogenous realization.

## 6. One trajectory only; no scenario ensemble in V1 (5.6; user restriction)

A05.5 V1 supplies **exactly one point-forecast trajectory** of length `H` per issue time and episode seed. Conceptual A05.4 optional scenario/member/quantile/dispersion extensions are **reserved and inactive**; do not instantiate a scenario axis of size greater than one, Monte Carlo ensembles, stochastic branching, user covariance matrices, cross-channel covariance models, or scenario weights in V1. Primitive errors for distinct keys may be independently generated by their stable seed substreams; physical dependence of derived quantities is retained through Section 4. There is no custom correlation-model interface to implement.

This permits ordinary deterministic MPC/RL/RBC experiments using identical noisy-forecast tapes without bringing in stochastic MPC or scenario tree infrastructure.

## 7. Controller fairness and scientific claims (5.7)

For a controlled P1 comparison, RBC, MPC and RL must see the same realized plant inputs and the same **permitted** one-trajectory forecasts for an identical run/source/seed configuration; repeat the principle independently for P2. Controllers may elect not to use permitted forecasts. Forecast generation must not depend on controller identity, device control requests, rewards, or the order in which algorithms call the service. Protected full source future truth and pre-/post-noise audit remain outside normal controller observation unless A05.6 explicitly authorizes specific fields.

**Reporting distinction:** the `none`/`sigma=0` configuration is a perfect-exogenous-foresight/oracle diagnostic because A05.4's source at `k+ell` is actual future truth. Positive additive Gaussian errors create a **controlled synthetic forecast-error benchmark**, not an operationally causal forecasting model. Both comparisons should carry the method and error magnitude in saved provenance and plots.

## 8. Replay, failures, evidence and implementation qualification (5.8)

All A05.2/A05.3 validation carries through unchanged: exact declared sources/bindings/units, CSV/Parquet parity, UTC/DST conversion, approved interpolation/holds, default `tile`, opt-in `strict`, missing/duplicate/nonfinite failure, and no implicit future truth substitution outside the ratified forecast basis. If a required forecast lead lacks valid source coverage in strict mode, return a typed forecast-coverage error; do **not** invent a forecast, mutate Plant, or prematurely stop an otherwise valid physical episode. A05.6 determines whether a controller may continue without the requested forecast.

Protected evidence retains source/binding/content SHA, episode identity, external logical t0/dt/decision index, physical source index and replay cycle, issued/valid timestamps, horizon/lead, channel/entity/units, noise mode, sigma vector or expansion rule, seed derivation/version, raw or conditioned draw, any clipping/bound handling, noisy prediction and scientific labeling. An H0-to-H3 audit/history policy may retain appropriate identities without inadvertently publishing hidden future truth to the controller.

Before executable A05 runtime qualification, demonstrate:

1. Identity/no-noise equality; only additive Gaussian configurations accepted; multiplicative/uniform/scenario counts greater than one rejected.
2. Per-channel/entity/lead sigma dimension/unit validation, constant versus explicit lead-dependent values and zero-sigma exactness.
3. Physical-domain conditioning/explicit clipping with recorded provenance; correct load PF and Faiman PV derivations.
4. Repeat-call/order/reset/seed and independent-environment reproducibility; distinct logical issue noise even under source tiling.
5. Cross-controller equality of truth/forecast inputs for matched configurations and no forecast read causing AltDSS writes or solves.
6. Strict/tile source coverage, negative tests for missing/malformed values and true decision vs electrical sample timestamp alignment.
7. A04 and A05.1-A05.4 whole-predecessor regressions, hash-pinned 203-file manifest and qualified successor source receipt.

**Disposition:** A05.5.1-A05.5.8 DESIGN RATIFIED with user-limited **additive Gaussian or no noise** and **one seeded forecast trajectory, no scenario ensemble**, without any A05 executable source authorization. A05.6 (information visibility) and A05.7 (dynamic events/qualification) remain before the A05 implementation gate.
