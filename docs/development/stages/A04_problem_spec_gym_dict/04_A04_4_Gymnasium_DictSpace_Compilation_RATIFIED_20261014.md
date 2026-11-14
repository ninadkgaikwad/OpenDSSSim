# A04.4 - Gymnasium Dict-Space Compilation

**Date ratified:** 2026-10-14
**Status:** RATIFIED
**Runtime implementation authorized by this document:** No

## Purpose

A04.4 defines deterministic compilation from already-resolved semantic observation/action contracts into canonical Gymnasium spaces.

```text
ResolvedObservationSpec + ResolvedActionSpec
                |
                v
       deterministic compiler
                |
                v
Gymnasium observation_space + action_space
```

A04.2 decides controller-visible observations. A04.3 decides controller actions. A04.4 only compiles those resolved semantics into fixed Gymnasium spaces. A04.5 owns state-dependent admissibility, faults/device availability, and NATIVE/EXTERNAL/HYBRID authority.

## Canonical Spaces Are Nested Gymnasium Dict Spaces

The generalized OpenDSSSim plant uses semantic nested Gymnasium `Dict` spaces and runtime values.

Conceptual observation:

```python
{
    "current": {
        "Bus": {"650": {"pu_voltage": ...}},
        "PVSystem": {"PV1": {"P": ..., "Q": ...}}
    },
    "forecast": {
        "Load": {"Load1": {"kW": ...}}
    }
}
```

Conceptual action:

```python
{
    "PVSystem": {
        "PV1": {"kvar": ...},
        "PV2": {"kvar": ...}
    },
    "Capacitor": {
        "Cap1": {"state": ...}
    }
}
```

Canonical plant values are semantic dictionaries, not opaque vectors.

## Compiler Input Is Resolved Semantics Only

The compiler consumes `ResolvedProblemSpec`, including resolved observation/action semantics, selector ordering, static bounds/domains, and provenance. It performs no new AltDSS discovery and does not re-run semantic queries.

Conceptually:

```text
CompiledGymSpaces
├── observation_space
├── action_space
├── observation_layout
├── action_layout
├── observation_space_sha256
├── action_space_sha256
└── gym_space_contract_sha256
```

## Deterministic Ordering

Ordering stored in the `ResolvedProblemSpec` is authoritative. Gym/default mapping sorting or backend iteration order may not redefine semantic ordering.

Named groups remain metadata/ordering constructs; they do not replace native OpenDSS class/object/quantity keys with anonymous indices.

## Continuous Quantities and Selectors

Continuous quantities compile to `Box`, canonically using `float64`.

Selectors such as phase, terminal, conductor, or winding become deterministic fixed leaf axes with explicit selector-order metadata.

Example:

```text
Bus.650.pu_voltage
shape = (3,)
selector axis = [phase_1, phase_2, phase_3]
```

## Forecast Shapes

Forecast observations must have fixed resolved shapes before runtime compilation.

Conceptually:

\[
\hat{x}_{t+1:t+H}
\]

maps to a fixed numeric leaf such as:

```text
shape = (H, *native_quantity_shape)
```

Variable-length core forecast spaces are not part of A04.4. A05 later owns the forecast provider, horizon, uncertainty/error, and seed semantics.

## Discrete Actions

Discrete semantic actions may use `Discrete`, `MultiDiscrete`, or `MultiBinary` only when the representation is lossless and reversible.

A04.4 may not silently replace semantic/native values with opaque category codes.

## Static Gym Action Domain Versus State-Dependent Admissibility

The Gym action space is a static outer interface:

\[
\mathcal{U}_{\mathrm{admissible}}(x_t)
\subseteq
\mathcal{U}_{\mathrm{Gym}}.
\]

State-dependent, coupled, topological, fault-related, availability-related, and authority-related restrictions belong to A04.5.

The Gym space does not mutate when device state/topology/fault status changes.

## Bounds

Continuous external actions require deterministic static outer bounds from A03 intrinsic capability and/or a stricter `ProblemSpec` restriction. Missing required action bounds fail compilation.

Observation `Box` bounds may be infinite where legitimate. This does not weaken the fail-closed unreadable-value policy.

Static Gym bounds are distinct from state-dependent/coupled constraints such as:

\[
P^2 + Q^2 \le S_{\mathrm{rated}}^2.
\]

## Runtime Space Validation

Canonical observations returned by reset/step must satisfy the observation space.

Requested canonical actions supplied to `step()` must satisfy the action space before A04.5 admissibility checks.

```text
Gym structural/domain validation
          |
          v
A04.5 physical/control admissibility
```

## Fail-Closed Compilation

Semantic path collisions, unresolved shapes, unsupported dtypes/domains, inconsistent bounds, ambiguous selector order, or incompatible semantic-to-space mappings fail compilation.

No implicit merging, substitution, dummy channels, or padding is allowed.

Empty action `Dict({})` remains valid for no-external-control cases.

## Controller Adapters Own Controller-Specific Representations

The canonical plant remains:

```text
semantic observation Dict
semantic action Dict
```

Controller-specific adapters may transform them:

- RBC: may consume/construct semantic Dicts directly.
- MPC/optimization: may map Dicts to deterministic vectors/matrices and solver outputs back to semantic action Dicts.
- RL: may consume Dict observations via multi-input/custom extractors or explicit flattening/normalization; where the RL algorithm requires a non-Dict action space, an adapter converts its action representation back to the canonical semantic action Dict.

The plant itself does not flatten merely because a controller library prefers vectors.

## Reward / Termination / Truncation Use Rich Internal Semantic Context

OpenDSSSim internally retains semantic structures such as:

- observation Dict;
- requested action Dict;
- applied/admissible action Dict;
- realized action Dict.

Reward, termination, and truncation may also access a richer internal semantic runtime context containing full semantic state, disturbances, parameters, constraint/violation status, fault/device availability, solution status, time/episode state, and prior-step context where needed.

The controller-visible observation remains a selected subset:

\[
	ext{controller-visible observation}
\subseteq
	ext{environment-internal semantic context}.
\]

## Deterministic Traversal/Layout Metadata

Every compiled space has immutable deterministic traversal metadata, enabling reversible controller adapters.

Example:

```text
0 -> PVSystem.PV1.kvar
1 -> PVSystem.PV2.kvar
2 -> Capacitor.Cap1.state
```

Likewise observation selector components receive deterministic flat-layout identities when adapters need them.

## RNG Boundary

Gymnasium space seeding may support testing/sample generation but does not own simulator randomness.

A05/run provenance owns load/PV noise, forecast error, fault/event stochasticity, and physical uncertainty.

## Canonical Core Space Types

Unless later ratified otherwise, canonical compilation uses fixed-shape standard spaces only:

- `Dict`
- `Box`
- `Discrete`
- `MultiDiscrete`
- `MultiBinary`

Variable-length/custom core spaces are excluded from A04.4.

## Space Provenance

Compiled space provenance includes deterministic:

```text
observation_space_sha256
action_space_sha256
gym_space_contract_sha256
```

Canonical serialization includes semantic path, order, space type, shape, dtype, bounds/domain, selector mapping, forecast shape/horizon where applicable, and source semantic identity.

## Fault/Availability Boundary Carried Forward to A04.5

A fault association is a `ProblemSpec` concern and may target **any OpenDSS device/element**, not only lines.

A04.4 freezes the static-interface consequence only:

```text
faulted device
    -> remains semantically present
    -> action channels remain structurally present if normally selected
    -> Gym space structure remains fixed
```

A04.5 must ratify the generalized runtime semantics:

```text
fault association in ProblemSpec
    -> targeted device forced Enabled=False
    -> device unavailable/non-energized
    -> associated requested controls inadmissible while Enabled=False
    -> no controller may re-enable/re-energize the device through its normal action channels
```

The exact fault association schema, `Enabled=False` application, provenance, reset/runtime behavior, interaction with control authority, rejection reason/status, and admissibility enforcement are A04.5 scope.

## A04.4 Ratification Decision

A04.4 is RATIFIED with these binding principles:

1. `ResolvedProblemSpec` is the sole semantic input to Gym-space compilation; no new AltDSS discovery occurs.
2. Canonical observation/action interfaces are nested Gymnasium `Dict` spaces.
3. OpenDSS class/object/quantity identity remains visible in canonical paths.
4. Named groups remain metadata/ordering constructs and do not replace native semantic keys.
5. Dict ordering comes from resolved semantic ordering.
6. Continuous physical quantities compile to `Box`, canonically using `float64`.
7. Selector sets become deterministic fixed axes with explicit selector-order metadata.
8. Forecast observations use fixed resolved shapes; no variable-length core forecast space.
9. Discrete semantics use standard discrete spaces only when representation is lossless/reversible.
10. Semantic/native values are not silently replaced by opaque category codes.
11. Continuous actions require deterministic static outer bounds.
12. Observation bounds may be infinite where legitimate without weakening fail-closed read semantics.
13. Static Gym bounds are distinct from state-dependent/coupled admissibility.
14. Observation/action spaces remain structurally immutable after construction.
15. Runtime observations/actions satisfy Gym structural/domain validation before physical admissibility checks.
16. Unsupported/ambiguous/colliding compilations fail closed.
17. Empty action `Dict` spaces remain valid; no dummy/padding channels are invented.
18. Canonical spaces remain controller-neutral; RBC/MPC/RL adapters own controller-specific transformations.
19. Semantic Dicts remain canonical internally; adapters may flatten/vectorize/normalize as needed.
20. Reward, termination, and truncation may use richer internal semantic context than the controller-visible observation.
21. Every compiled space has deterministic reversible traversal/layout metadata.
22. Gym space RNG is not simulator/exogenous randomness.
23. Canonical core space types are `Dict`, `Box`, `Discrete`, `MultiDiscrete`, and `MultiBinary`.
24. Observation/action/overall compiled-space SHA256 identities are first-class provenance.
25. Generalized `ProblemSpec` fault association for any OpenDSS device and `Enabled=False` fault lockout/admissibility semantics are mandatory A04.5 carry-forward requirements.
26. No A04 runtime implementation is authorized by this document.
