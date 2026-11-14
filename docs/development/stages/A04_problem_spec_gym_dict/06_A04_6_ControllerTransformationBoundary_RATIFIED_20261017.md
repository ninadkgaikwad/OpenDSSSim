# A04.6 - Controller-Side Transformation Boundary

**Date ratified:** 2026-10-17
**Status:** RATIFIED
**Runtime implementation authorized by this document:** No

## Purpose

A04.6 freezes the boundary between the canonical OpenDSSSim plant interface and controller-specific preprocessing.

For this OpenDSSSim version:

- OpenDSSSim does not derive controller features.
- OpenDSSSim does not own generic observation/action wrappers.
- OpenDSSSim does not flatten, normalize, reshape, tensorize, or otherwise preprocess controller observations/actions.
- Individual controller implementations own such transformations on their side.

The canonical plant contract remains:

```text
OpenDSSSim -> controller:
    canonical semantic observation Dict

controller -> OpenDSSSim:
    canonical semantic action Dict
```

## No Derived-Observation Layer in OpenDSSSim v1

OpenDSSSim v1 does not introduce a `DerivedObservationSpec`, `derived` namespace, derived-observation dependency graph, or derived-feature runtime.

Quantities such as voltage spread, voltage minimum/maximum, aggregate PV output, engineered controller features, custom feature vectors, or controller-specific latent quantities are controller-side preprocessing responsibilities unless a future separately ratified OpenDSSSim subsystem explicitly makes one of them a first-class simulator quantity.

## Canonical Observation Contract

The base environment returns only the semantic quantities explicitly selected by the resolved `ProblemSpec`.

```python
obs, info = env.reset()
obs, reward, terminated, truncated, info = env.step(action_dict)
```

`obs` is the canonical semantic observation Dict and `action_dict` is the canonical semantic action Dict.

## Controller-Side Observation Preprocessing

Each controller implementation may transform the canonical observation Dict as required.

- RBC may consume the semantic Dict directly.
- MPC may build controller-side vectors/matrices/parameters from it.
- RL may flatten, normalize, tensorize, encode, or apply custom feature extraction on its side.

OpenDSSSim does not prescribe or qualify a generic wrapper framework for these transforms in v1.

## No Generic Observation/Action Wrappers in OpenDSSSim v1

OpenDSSSim v1 does not take responsibility for generic observation flattening, normalization, standardization, tensor reshaping, graph encoders, history/frame-stack wrappers, or generic action-wrapper stacks.

Controllers may use any of those internally.

Before interacting with the plant, controller-side action logic must reconstruct the complete canonical semantic action Dict required by the resolved OpenDSSSim action contract.

## Controller Conversion Cannot Bypass the Plant

Controller-side preprocessing/conversion may not mutate AltDSS/OpenDSS directly.

All controller actions must enter through:

```text
controller
    -> canonical semantic action Dict
    -> OpenDSSSim.step()
    -> A04.4 Gym validation
    -> A04.5 finite-value / fault / authority checks
    -> AltDSS/OpenDSS
```

## Deterministic Layout Metadata Remains Available

The deterministic semantic ordering/layout ratified in A04.4 remains part of canonical resolved interface metadata.

Controller developers may use that metadata for reproducible vectorization/branch ordering, but OpenDSSSim does not need to perform flattening/unflattening for them.

## Controller-Side Preprocessing Provenance

Normalization statistics, feature engineering, graph/tensor encoders, action encodings, running statistics, frame stacking, and other preprocessing state belong to the controller workflow, not OpenDSSSim v1.

## No Hidden Information Gain

Controller-side preprocessing may operate only on information legitimately supplied through the canonical controller-visible observation and other explicitly granted controller inputs.

It may not use preprocessing as a route to hidden OpenDSSSim state.

## Reward / Termination / Truncation Hooks Remain Plant Responsibilities

Reward, termination, and truncation are not controller-side wrappers.

OpenDSSSim owns their invocation points as part of the environment lifecycle.

The plant/environment exposes abstract callable hooks conceptually equivalent to:

```text
reward(...)
termination(...)
truncation(...)
```

The exact typed signatures and runtime binding are finalized in A04.7.

These hooks receive the proper canonical observation/action and/or runtime semantic values required by their contract, not controller-preprocessed representations.

## Default and Custom Reward

OpenDSSSim provides a default reward implementation.

A `ProblemSpec` may instead supply a custom reward callable.

The plant invokes either the default or the ProblemSpec-resolved custom callable through the same reward hook.

Custom reward functions may not bypass plant semantics or mutate AltDSS/OpenDSS.

## Default and Custom Termination

OpenDSSSim provides a default termination implementation.

A `ProblemSpec` may supply a custom termination callable.

The plant invokes the resolved termination function internally at the proper step boundary.

Termination remains distinct from truncation.

## Default and Custom Truncation

OpenDSSSim provides a default truncation implementation.

A `ProblemSpec` may supply a custom truncation callable.

The plant invokes the resolved truncation function internally using the canonical runtime information defined by A04.7.

## Callable Provenance

Custom reward, termination, and truncation callables supplied through `ProblemSpec` must have recorded identity/provenance.

Exact callable signatures, serialization constraints, and runtime binding rules are A04.7 scope.

## Controller Representation Does Not Redefine Plant Hooks

A controller may flatten or normalize its observation internally, but reward/termination/truncation remain functions of canonical plant/runtime semantic information.

Controller-preprocessed representations are not authoritative plant state.

## Temporal Preprocessing

A04.6 does not create a generalized plant-side history/frame-stack transformation layer.

Controller-side temporal preprocessing may exist in controller code.

A05 remains authoritative for simulator time, exogenous profiles, forecasts, fault/repair events, and other time-dependent plant contracts.

## `problem=None`

No-control/native simulation remains valid.

A `problem=None` run requires no controller preprocessing contract and uses default plant reward/termination/truncation behavior as defined by the runtime contract.

## Ratification Decision

A04.6 is RATIFIED with these binding principles:

1. OpenDSSSim v1 does not implement derived controller observations/features.
2. There is no OpenDSSSim v1 `DerivedObservationSpec` or derived-observation runtime.
3. Controller feature engineering is controller-side preprocessing.
4. OpenDSSSim v1 does not implement generic observation wrappers.
5. OpenDSSSim v1 does not implement generic action wrappers.
6. The canonical plant remains semantic observation Dict -> controller and semantic action Dict -> plant.
7. RBC, MPC, and RL may preprocess the same canonical Dict differently on their own side.
8. Controller-side action conversion must reconstruct the complete canonical semantic action Dict.
9. Controller-side code may not bypass `env.step()` or mutate AltDSS/OpenDSS directly.
10. A04.4 deterministic semantic layout metadata remains available, but OpenDSSSim does not have to flatten/unflatten for controllers.
11. Controller-side normalization/feature/action-encoding provenance belongs to the controller workflow.
12. Controller preprocessing may not gain access to hidden plant information beyond explicitly granted inputs.
13. Reward, termination, and truncation remain plant/environment invocation hooks.
14. OpenDSSSim provides default reward, termination, and truncation implementations.
15. `ProblemSpec` may supply custom reward, termination, and truncation callables.
16. Plant hooks receive proper canonical observation/action and/or runtime semantic inputs, not controller-preprocessed representations.
17. Custom callable identity/provenance is recorded.
18. Exact callable signatures/binding/serialization are finalized in A04.7.
19. A04.6 adds no generalized plant-side history/frame-stack transformation contract.
20. A05 remains authoritative for simulator temporal/exogenous/forecast/event contracts.
21. `problem=None` remains valid.
22. No A04 runtime implementation is authorized by this document.
