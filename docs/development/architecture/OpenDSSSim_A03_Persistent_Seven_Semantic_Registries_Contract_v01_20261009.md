# OpenDSSSim A03 Persistent Seven Semantic Registries Contract

## 1. Identity

- Contract ID: `OpenDSSSim_A03_Persistent_Seven_Semantic_Registries_Contract_v01_20261009`
- Documentation patch: `OpenDSSSim_A03D1_SemanticRegistries_DocumentationFreeze_v01_20261009`
- Date: 2026-10-09
- Status: **FROZEN FOR A03 IMPLEMENTATION**
- Physical predecessor: `OpenDSSSim_A02H1_Persistent_Circuit_Inventory_Native_Control_Discovery_v01R1_20261008`
- A02H1 qualified source-manifest SHA256:
  `7A19A87AA59BA5615A75C222C704F06D2E153D730871B09F262264927DC4723F`
- Environment: `scalebridge-dev-gpu-laptop`
- A03 directed-input SHA256:
  `4EEAB2699A9F7DC1344CFD69A37BE1B0692F793D58B07B650DF667D60F62BA30`

## 2. Objective

A03 consumes a validated A02H1 `CircuitInventory` and builds/persists the semantic model
used by future `ProblemSpec`, controller compatibility, observation/state, and action
layers.

A03 answers:

> **What does the physically discovered circuit mean to OpenDSSSim?**

## 3. Required registries

One `SemanticRegistryBundle` must contain:

1. `CircuitRegistry`
2. `StateRegistry`
3. `ActionRegistry`
4. `DisturbanceRegistry`
5. `ConstraintRegistry`
6. `ParameterRegistry`
7. `CapabilityRegistry`

## 4. Frozen address families

```text
NativePropertyAddress
RuntimeReadoutAddress
RuntimeCommandAddress
```

## 5. Frozen mutability classes

```text
READ_ONLY
INIT_ONLY
STEP_CONTROLLABLE
STEP_EXOGENOUS
```

## 6. Frozen semantic invariants

1. writable AltDSS property != external action;
2. `StateRegistry` != observation space;
3. `ActionRegistry` != every problem's action space;
4. native OpenDSS controller capability != external OpenDSSSim authority;
5. semantic definition != live runtime value;
6. solved runtime readout need not be represented as a fake DSS property;
7. intrinsic plant constraint != problem-specific operating requirement;
8. parameter and disturbance roles are explicitly classified;
9. generalized semantics must not hard-code IEEE-123 object names;
10. controllers never mutate AltDSS directly.

## 7. Semantic compilation

A03 may use:

```text
validated CircuitInventory
+ frozen semantic policy
+ one-time explicit read-only static metadata extraction
```

A03 must not rerun full A02 physical discovery when A02H1 inventory is valid.

## 8. Persistence/invalidation

Registry reuse depends on:

- A02H1 inventory semantic identity;
- source-tree identity;
- A03 registry schema identity;
- semantic-policy version;
- semantic-policy SHA256;
- backend identity;
- compatible AltDSS/DSS engine identity.

Semantic-policy changes invalidate the registry even if DSS sources are unchanged.

## 9. Native controls

A03 records native-control capability/configuration semantics separately from physical
external action endpoints.

Examples:

```text
RegControl.VReg -> native-controller parameter/configuration
Transformer tap command -> physical action endpoint

CapControl settings -> native-controller parameter/configuration
Capacitor state command -> physical action endpoint
```

## 10. Controller-science bridge

A03 supplies the capability/native-object registry requirements currently identified by
the controller-science track.

Future `ProblemSpec`/controller compatibility must support explicit `SUPPORTED` or
`UNSUPPORTED` outcomes with no silent substitution.

## 11. Non-goals

A03 does not implement:

- final `ProblemSpec`;
- final Gym action/observation spaces;
- control-authority switching;
- time-series/forecast execution;
- requested/applied/realized action execution;
- controller implementations;
- MPC/RL;
- paper-specific IEEE-123 selections.

## 12. Detailed stage authority

The detailed, ratified engineering contract is under:

`docs/development/stages/A03_semantic_registries/`

Those files are normative for the A03 source implementation.

## 13. Successor boundary

A04 consumes the persistent A03 semantic bundle and selects problem-authorized
state/action/disturbance/constraint surfaces through `ProblemSpec`.
