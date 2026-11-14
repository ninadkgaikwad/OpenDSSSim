# A04.3 - Action Selection

**Date ratified:** 2026-10-13  
**Status:** RATIFIED  
**Runtime implementation authorized by this document:** No  
**Parent stage:** A04 - ProblemSpec + problem-specific Gymnasium Dict spaces

## 1. Purpose

A04.3 defines how a `ProblemSpec` selects and authorizes controller action channels from the A03 semantic action surface.

```text
A03 ActionRegistry
    =
all plant command channels recognized by A03
as legitimate external-control semantics

ActionSpec
    =
which legitimate A03 action channels this ProblemSpec
allows its controller to command

ResolvedActionSpec
    =
the exact concrete ordered action channels
for this circuit/controller-specific problem
```

Conceptually,

\[
\mathcal{A}_{\mathrm{problem}}
\subseteq
\mathcal{A}_{\mathrm{A03}}.
\]

A04.3 does not compile Gymnasium `Space` objects; that is A04.4. Detailed NATIVE / EXTERNAL / HYBRID ownership and coordination are A04.5.

## 2. A03 ActionRegistry Is the Raw Action Authority

A raw controller action may select only semantics already present as legitimate A03 `ActionRegistry` entries.

A04 may not create an external action merely because an OpenDSS property is writable.

```text
writable DSS property
    !=
STEP_CONTROLLABLE semantic
    !=
action authorized by this ProblemSpec
```

Candidate action families include, when registered by A03:

- PVSystem reactive-power commands;
- Storage active/reactive-power commands;
- capacitor switching commands;
- transformer/regulator tap commands;
- switchable-line open/close commands.

A04 does not broaden the frozen A03 semantic policy.

## 3. READ_ONLY and INIT_ONLY Quantities Are Not Step Actions

`READ_ONLY` quantities cannot be controller step actions.

`INIT_ONLY` quantities may participate in initialization/problem configuration, but are not per-step actions.

```text
INIT_ONLY
    -> initialization / configuration

STEP_CONTROLLABLE
    -> candidate ActionSpec channel
```

Native-controller configuration parameters are not automatically action-vector components.

## 4. Canonical Action Dictionary Preserves OpenDSS-Native Identity

The canonical action structure preserves A03/OpenDSS identities:

```text
<Class>
    |
    v
<ObjectName>
    |
    v
<ActionQuantity>
    |
    v
selectors where required
```

Conceptually:

```python
action = {
    "PVSystem": {
        "PV1": {"kvar": ...},
        "PV2": {"kvar": ...},
    },
    "Capacitor": {
        "Cap1": {"state": ...},
    },
    "Transformer": {
        "RegX": {"tap": ...},
    },
    "Line": {
        "SW1": {"open_close": ...},
    },
}
```

Opaque numeric action indices are not the canonical semantic interface. Flattened/vector/tensor representations may be constructed later by deterministic adapters.

## 5. Supported Action Selection Mechanisms

A04.3 supports:

1. exact semantic references;
2. semantic queries;
3. named and ordered groups.

Exact references and queries may be mixed. Queries resolve against A03 semantics, not by direct AltDSS enumeration.

## 6. Explicit Cardinality Requirements

Action queries use explicit cardinality contracts:

- `ANY`
- `NONEMPTY`
- `EXACT(n)`
- `RANGE(min,max)`

A mismatch is a resolution failure. A request for ten action channels must not silently resolve to nine.

## 7. One-Time Deterministic Resolution

Action selection resolves once during `ResolvedProblemSpec` construction.

```text
ProblemSpec
    +
A03 ActionRegistry
    |
    v
strict one-time resolution
    |
    v
ResolvedActionSpec
```

Registry queries do not re-run every environment step.

## 8. Canonical Action Values Use Registered Physical / Native Semantics

Canonical action values use the registered physical/native meanings and units of their A03 channels.

Examples:

```text
PVSystem.PV1.kvar
Storage.BESS1.P
Storage.BESS1.Q
Capacitor.Cap1.state
Transformer.RegX.tap
Line.SW1.open_close
```

Algorithm-specific normalization/encoding does not redefine canonical meaning.

```text
canonical action
    =
physical / semantic command

controller encoding
    =
optional deterministic transformation
```

## 9. A04 Does Not Silently Reinterpret Action Meaning

A04 may select an action semantic but may not silently change it.

An absolute tap target cannot silently become raise/lower. A capacitor state command cannot silently become toggle unless toggle is the registered semantic.

Any future action transformation must be explicit, deterministic, provenance-bearing, and terminate in a registered canonical A03 action channel.

## 10. Canonical Action Is Total at Each Control Step

Every selected external action channel receives an explicit requested command at every control step.

Omission does not implicitly mean:

- hold;
- repeat previous command;
- zero command;
- native takeover;
- no-op.

A hold/no-op is valid only when explicitly part of the registered/ratified action semantics. Sparse/event-driven encodings require an explicit adapter.

## 11. Requested, Applied/Admissible, and Realized Actions Remain Distinct

A04 preserves:

\[
u_t^{\mathrm{req}}
\rightarrow
u_t^{\mathrm{app}}
\rightarrow
u_t^{\mathrm{real}}.
\]

- **requested**: exact controller command;
- **applied/admissible**: what OpenDSSSim actually submits after an explicitly configured validation/projection/supervision policy;
- **realized**: post-solve physical/control value actually achieved.

If no admissibility transformation is configured, applied equals requested.

No clipping, rescue, fallback, substitution, or projection may occur silently.

## 12. Problem Restrictions May Narrow but Never Enlarge Intrinsic Capability

A problem-level action restriction may be stricter than the intrinsic A03/device capability, but may never enlarge it:

\[
\mathcal{A}_{\mathrm{problem}}
\subseteq
\mathcal{A}_{\mathrm{plant}}.
\]

Detailed constraint intersection is A04.5.

## 13. Semantic Action Kind Is Recorded; Gym Encoding Is Deferred

A04.3 records semantic action kind, such as:

- continuous;
- binary;
- discrete categorical;
- ordered discrete/integer.

A04.4 decides the concrete Gymnasium representation (`Box`, `Discrete`, `MultiDiscrete`, `MultiBinary`, `Dict`).

## 14. Controller-Specific ProblemSpecs and Same-Resource Fairness

Controller-specific `ProblemSpec` instances may differ in controller-facing encoding.

If an experiment claims same-resource comparison across RBC, MPC, and RL, their resolved physical action authority must refer to the same underlying A03 plant channels.

Different resource populations require an explicitly different documented experiment.

## 15. Control Authority Boundary

Inclusion in `ActionSpec` means the problem requests controller authority over that registered channel.

A04.3 does not itself resolve ownership under:

- `NATIVE`;
- `EXTERNAL`;
- `HYBRID`.

Those rules are A04.5. A04.3 must not silently disable native controls or transfer ownership.

## 16. Native Controller Objects Are Not Automatically External Actions

OpenDSS native control objects such as `RegControl`, `CapControl`, `InvControl`, `SwtControl`, and `StorageController` represent native-control capability/configuration.

Their presence does not make every writable property an external controller action.

Native control capability and external action authority remain distinct.

## 17. No Raw Custom Action Callback May Bypass A03

A raw problem action callback may not directly mutate AltDSS.

Forbidden:

```python
def action_fn(dss, u):
    dss.some_object.some_property = ...
```

Allowed future direction:

```text
controller encoding
    |
    v
explicit deterministic transformation
    |
    v
canonical registered A03 action dictionary
    |
    v
runtime action binding
```

## 18. Action Selection and Coupled Constraints Are Separate

Selecting multiple action channels does not define their joint admissible region.

For example,

\[
P^2 + Q^2 \le S_{\mathrm{rated}}^2
\]

belongs to the constraint layer.

```text
A04.3
    -> selects action channels

A04.5
    -> resolves/enforces coupled admissibility
```

## 19. Conceptual Schemas

```text
ActionSpec
|
+-- groups[]
|    +-- group_id
|    +-- selections[]
|    |     +-- ExactSemanticRef
|    |     +-- SemanticQuery
|    +-- cardinality_requirement
|    +-- ordering_policy
|    +-- optional problem-level action restriction
|
+-- metadata
```

Resolution produces:

```text
ResolvedActionSpec
|
+-- groups[]
|    +-- group_id
|    +-- ordered_channels[]
|          +-- semantic_id
|          +-- native class
|          +-- native object name
|          +-- action quantity
|          +-- selectors
|          +-- semantic action kind
|          +-- physical/native units
|          +-- intrinsic capability references
|          +-- runtime command address reference
|
+-- action_contract_identity
```

## 20. A04.3 Ratification Decision

A04.3 is RATIFIED with these binding decisions:

1. `ActionRegistry`, `ActionSpec`, and `ResolvedActionSpec` are distinct.
2. Raw controller actions select only legitimate A03 `ActionRegistry` entries.
3. Writable DSS properties, native-control configuration, `READ_ONLY`, and `INIT_ONLY` quantities do not automatically become step actions.
4. Canonical action structures preserve OpenDSS class/object/action-quantity/selectors in dictionary form.
5. Exact references, queries, and named ordered groups are supported and may be mixed.
6. Queries use `ANY`, `NONEMPTY`, `EXACT(n)`, or `RANGE` cardinality requirements.
7. Resolution occurs once and is deterministic.
8. Canonical action values use registered physical/native semantics and units.
9. A04 cannot silently reinterpret absolute, incremental, toggle, normalized, or other action meanings.
10. Canonical actions are complete/total each control step; omission has no implicit hold/no-op semantics.
11. Requested, applied/admissible, and realized actions remain separately defined and auditable.
12. No clipping, rescue, projection, fallback, or substitution occurs silently.
13. Problem restrictions may narrow but never enlarge intrinsic A03 capability.
14. A04.3 records semantic action kind; Gymnasium space compilation is A04.4.
15. Controller-specific specs may differ in representation, but fair same-resource comparisons use the same physical A03 action channels unless explicitly documented otherwise.
16. No raw custom action function may directly mutate AltDSS.
17. NATIVE / EXTERNAL / HYBRID ownership resolution is A04.5.
18. Coupled action constraints are A04.5.
19. No A04 runtime implementation is authorized by this document.
