# A04.2 — Observation / State Selection

**Date ratified:** 2026-10-12  
**Status:** RATIFIED  
**Runtime implementation authorized by this document:** No  
**Parent stage:** A04 — ProblemSpec + problem-specific Gymnasium Dict spaces

## 1. Purpose

A04.2 defines how a `ProblemSpec` selects information visible to a controller. The complete A03 plant state is not automatically the controller observation.

```text
A03 semantic read surface
        |
        v
ObservationSpec
        | strict one-time resolution
        v
ResolvedObservationSpec
        |
        v
canonical controller-visible observation dictionary
```

## 2. Distinct Information Categories

Plant state, current disturbance, static parameter, future forecast, and controller observation are not interchangeable. A raw observation may reference registered semantics from `StateRegistry`, `DisturbanceRegistry`, and `ParameterRegistry`, while future exogenous values may be supplied as explicitly selected forecast views through the later A05 forecast/exogenous service. Each resolved channel retains source provenance.

## 3. Canonical Observation Dictionary Uses OpenDSS-Native Identity

The canonical controller-facing structure preserves A03/OpenDSS identity, conceptually:

```text
current / forecast
        -> Class
            -> ObjectName
                -> Quantity
                    -> selectors where required
```

Example concept:

```python
obs = {
    "current": {
        "Bus": {"650": {"pu_voltage": ...}},
        "PVSystem": {"PV1": {"P": ..., "Q": ...}},
    },
    "forecast": {
        "Load": {"Load1": {"kW": [...]}},
        "PVSystem": {"PV1": {"available_power": [...]}},
    },
}
```

Exact Gymnasium nesting/space types are deferred to A04.4. Native semantic identity must not be replaced by opaque numeric channel IDs.

## 4. Deterministic Ordering Over the Dictionary Convention

Ordering exists for deterministic hashing, serialization, flattening/vectorization, MPC vector construction, RL tensors, and adapters. It does not replace semantic keys. Explicit authored ordering is preserved. Query-generated selections use deterministic canonical semantic ordering over native identities and selectors.

## 5. Supported Selection Mechanisms

A04.2 supports:

1. exact semantic references;
2. semantic queries resolved against A03;
3. named/ordered groups.

These mechanisms may be mixed within one observation contract.

## 6. Explicit Cardinality Contracts

Queries must carry explicit cardinality semantics such as `ANY`, `NONEMPTY`, `EXACT(n)`, and `RANGE(min,max)`. Unsatisfied cardinality causes explicit resolution failure. Resolved counts become part of provenance.

## 7. Future Exogenous / Forecast Observation

Controller observations may include future load, PV availability, weather/exogenous drivers, and other problem-authorized forward views. Forecasting must not advance or mutate AltDSS.

```text
true exogenous trajectory
        +--> physical simulator
        +--> forecast service
                +--> perfect forecast
                +--> forecast-error model
                        -> controller observation
```

The physical simulator always evolves using the authoritative true exogenous trajectory.

## 8. Forecast Error

A problem/controller observation contract may request reproducible forecast error. Additive Gaussian/normal error is explicitly allowed, for example

\[
\widehat{{x}}_{{t+k}} = x_{{t+k}} + \epsilon_{{t+k}},
\qquad \epsilon_{{t+k}} \sim \mathcal{{N}}(\mu,\sigma^2).
\]

Forecast error requires seed/configuration provenance. Exact horizon, lead-time dependence, bias, covariance/correlation, clipping/physical-domain projection, seed ownership, and persistence are deferred to A05/A04 integration design. Noisy forecasts do not alter the true physical exogenous trajectory.

## 9. One ProblemSpec per Problem-Type / Controller-Type Combination

The schema is controller-neutral, but instances may be controller-type specific:

```text
P1 + RBC -> P1_RBC_ProblemSpec
P1 + MPC -> P1_MPC_ProblemSpec
P1 + RL  -> P1_RL_ProblemSpec
P2 + RBC -> P2_RBC_ProblemSpec
P2 + MPC -> P2_MPC_ProblemSpec
P2 + RL  -> P2_RL_ProblemSpec
```

Controller-specific specs may expose different information structures where scientifically intended, e.g. MPC forecast horizons not used by a simple rule controller.

## 10. Common Physical Problem Fairness Boundary

Controller-specific `ProblemSpec` instances remain subordinate to the same common physical problem contract. Within a common problem type, scientific comparison preserves as applicable the feeder, physical disturbances, controllable-resource population, intrinsic limits, experiment horizon, authoritative true exogenous realization, and evaluation/fairness requirements.

## 11. No Automatic Information Leakage

Registered does not mean controller-visible. Hidden current, diagnostic, parameter, or future information remains hidden unless explicitly selected.

## 12. Raw Observation Selection Cannot Bypass A03

A04.2 raw observation selection does not permit arbitrary direct-AltDSS callbacks. Derived functions are deferred to A04.6 and operate from authorized registered inputs rather than direct backend access.

## 13. Resolution Happens Once

Registry queries execute during problem resolution, not on every `env.step()`. Runtime reads use already-resolved semantic addresses.

## 14. Missing Runtime Observation Values

A resolved channel may not silently become zero, NaN, stale previous data, a substituted quantity, or a different semantic channel. Exact runtime error/missing-data handling is deferred to A04.7.

## 15. Parameters and Forecasts Need Not Be Repeated as Dynamic State

A parameter may be available in controller context without being duplicated at every dynamic step. Required physical disturbances and forecast services are not automatically exposed unless selected into the controller-visible observation. Conceptually:

```text
ResolvedProblemSpec
+-- observation_view
+-- parameter_view
+-- disturbance_view
+-- forecast_requirements
```

## 16. Ratification Decision

A04.2 is RATIFIED. Binding decisions are: observations are explicit selected views; raw selections resolve through A03 semantics; current state/disturbance/parameter and future forecast information may be selected; canonical observations are OpenDSS-native dictionaries; deterministic ordering applies over those dictionaries for reproducibility/vectorization; exact references/queries/groups may mix; queries have explicit cardinality; reproducible forecast error including additive Gaussian error is permitted; true exogenous data drives physics; one `ProblemSpec` instance is used per `(problem type, controller type)` combination while preserving a common physical problem fairness contract; raw observation callbacks may not bypass A03; resolution occurs once; and missing reads cannot silently change semantics. No runtime implementation is authorized by this document.
