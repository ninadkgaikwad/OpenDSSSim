# A04.1 — ProblemSpec Core Contract

**Date ratified:** 2026-10-12  
**Status:** RATIFIED  
**Runtime implementation authorized by this document:** No  
**Parent stage:** A04 — ProblemSpec + problem-specific Gymnasium Dict spaces

## 1. Purpose

A04.1 defines the core contract for representing a control problem above the A03 semantic registries and below controller implementations.

```text
A01-A03 physical + semantic authority
        |
        v
ProblemSpec
        | strict resolution
        v
ResolvedProblemSpec
        |
        +--> later Gym-space compilation
        +--> later runtime binding
        +--> controller-specific runtime use
```

## 2. ProblemSpec and ResolvedProblemSpec

`ProblemSpec` and `ResolvedProblemSpec` are distinct first-class, logically immutable schemas. `ProblemSpec` is the authored control-problem definition. `ResolvedProblemSpec` is the exact circuit/A03-resolved realization. `ProblemSpec` does not mutate into `ResolvedProblemSpec`.

`ResolvedProblemSpec` binds the authored problem to one A03 `SemanticRegistryBundle`, one circuit/inventory identity, exact semantic selections, exact capability satisfaction, exact later-ratified ordering/grouping, exact authority compatibility, and a deterministic resolved identity.

## 3. A03 Remains Semantic Authority

A04 may select, organize, restrict, and compose semantics already known to A03. It may not invent native DSS addresses, redefine A03 meaning, convert arbitrary writable properties into actions, or bypass registries through direct AltDSS enumeration/mutation.

```text
A03: What does the plant contain and what does each quantity/capability mean?
A04: Which legitimate plant semantics does this control problem use?
```

## 4. Optional Control Problem

`problem=None` remains valid. OpenDSSSim continues to support native-controlled or externally driven time-series simulation without an external control problem.

## 5. Controller-Neutral Schema

The generalized `ProblemSpec` schema is controller-neutral. Controller implementation details such as MPC horizon/solver, LinDistFlow implementation, optimizer tolerances, RL algorithm/architecture, discount factor, learning rate, replay buffer, checkpoints, training seeds, and rule-controller tuning do not belong in the generalized schema.

A04.2 later refines this by allowing one `ProblemSpec` instance per `(problem type, controller type)` combination.

## 6. Problem Constraints May Narrow but Not Contradict Plant Physics

A problem may impose a stricter admissible domain than A03 intrinsic plant/device capability, but may not enlarge or redefine intrinsic physical capability. Conceptually,

\[
\mathcal{{U}}_{{\mathrm{{problem}}}} \subseteq \mathcal{{U}}_{{\mathrm{{plant}}}}.
\]

Exact mechanics are deferred to A04.5.

## 7. Strict Atomic Resolution

Resolution is fail-closed and atomic. It must not silently drop missing selections, shrink requested cardinality, substitute another semantic quantity, clip an invalid requirement, fall back to a different device/control class, or rescue an unsupported problem. Missing semantics, capability mismatch, invalid authority, conflicts, duplicates, and unsupported requirements produce explicit structured diagnostics.

## 8. Deterministic Identity

Two identities are required:

- `problem_spec_sha256`: canonical semantic identity of the authored `ProblemSpec`.
- `resolved_problem_sha256`: identity binding the authored spec to A03 semantic-bundle identity, circuit/inventory identity, exact resolved selections, semantically significant ordering/grouping, capability satisfaction, and authority contract.

A semantic change changes the corresponding identity. Mapping keys may be canonically sorted, while semantically meaningful ordered sequences retain authored/resolved order.

## 9. Runtime Immutability

Once a `ResolvedProblemSpec` is established for a run/episode, its semantics cannot mutate silently. Any semantic change requires a new resolved identity.

## 10. Reward, Termination, and Truncation Hooks

Reward, termination, and truncation belong to the optional problem/environment contract rather than being hidden inside controller implementations. OpenDSSSim provides defaults, and users may supply custom Python functions/callables, following the useful SmartCommunitySim pattern.

```text
RewardSpec      -> package default OR user callable
TerminationSpec -> package default OR user callable
TruncationSpec  -> package default OR user callable
```

Custom callables require stable identity/configuration and sufficient provenance so materially different code/configurations cannot masquerade as the same experiment. Exact signatures, defaults, serialization treatment, and invocation order are deferred to later A04 ratification.

## 11. Control Authority Modes

A04 supports `NATIVE`, `EXTERNAL`, and `HYBRID`. This supersedes the earlier A0 deferral of HYBRID. Exact HYBRID ownership/coordination semantics are deferred to A04.5, but must be explicit, deterministic, reproducible, and prohibit silent conflicting ownership of the same control channel.

The `ProblemSpec` declares required authority. Runtime owns the actual configured authority. Resolution verifies compatibility rather than silently reconfiguring it.

## 12. Conceptual Top-Level Shape

```text
ProblemSpec
|
+-- schema_version
+-- problem_id
+-- problem_version
+-- observations
+-- actions
+-- disturbances
+-- parameters
+-- constraints
+-- capability_requirements
+-- control_authority
+-- reward
+-- termination
+-- truncation
+-- metadata
```

Detailed subcontracts are ratified in later A04.x sections.

## 13. Ratification Decision

A04.1 is RATIFIED. Binding decisions are: distinct immutable `ProblemSpec`/`ResolvedProblemSpec`; A03 semantic authority; `problem=None`; controller-neutral schema; problem constraints may narrow but not contradict intrinsic plant limits; strict fail-closed resolution; authored/resolved deterministic identities; runtime immutability; default or user-defined reward/termination/truncation hooks with provenance; and support for `NATIVE`, `EXTERNAL`, and `HYBRID`. No runtime implementation is authorized by this document.
