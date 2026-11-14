# A04.7 - Runtime Binding, One-Time Preflight, and Qualification Boundary

**Date ratified:** 2026-10-18  
**Status:** RATIFIED  
**Runtime implementation authorized by this document:** No

## Purpose

A04.7 freezes how an already-resolved `ProblemSpec` is bound to `reset()`/`step()`, how plant hooks are invoked, what runtime information is recordable, and which checks are performed once before iterative simulation.

## 1. Already-resolved problem only

Runtime consumes the existing `ResolvedProblemSpec` and compiled A04.4 spaces. It does not rediscover OpenDSS objects, rerun semantic queries every step, substitute channels, change ordering, or mutate the resolved problem.

## 2. Immutable ProblemRuntimeBinding

A04.7 may introduce immutable execution infrastructure conceptually named `ProblemRuntimeBinding`. It binds exact observation readers, external-action writers, control-authority configuration, native-control suppression/configuration, static-fault `Enabled` handles, compiled-space identities, reward/termination/truncation hooks, and provenance.

## 3. Strict atomic binding

If any required observation reader, action writer, authority mechanism, native-control suppression mechanism, static-fault `Enabled` mechanism, custom hook, or identity cannot be bound exactly, the run does not partially start.

## 4. One-time identity verification

Circuit, inventory, A03 registry, resolved-problem, observation-space, and action-space identities are verified during run/episode initialization before the first iterative control step.

These checks are not repeated at every `step()` while the bound context is unchanged.

## 5. One-time run/episode initialization

Before the first control iteration:

```text
restore / compile baseline feeder
        ↓
verify circuit / registry / resolved-problem identity
        ↓
create or verify immutable ProblemRuntimeBinding
        ↓
configure NATIVE / EXTERNAL / HYBRID ownership
        ↓
apply static ProblemSpec faults
        ↓
fault targets -> Enabled=False
        ↓
apply initial externally supplied plant inputs
        ↓
AltDSS/OpenDSS solve
        ↓
read solution/status + required semantic values
        ↓
construct initial canonical observation Dict
        ↓
enter iterative loop on the same live AltDSS/OpenDSS context
```

This initialization is not rerun on every iteration. Ordinary iterative stepping preserves and evolves the same compiled context. An explicit new episode/reset may intentionally reinitialize the baseline.

## 6. `reset()` contract

`reset()` returns `(observation, info)`. It does not fabricate reward/termination/truncation. Failure to construct a valid initial state/observation is an explicit reset/runtime error.

## 7. Canonical `step()` pipeline

```text
canonical semantic action Dict
        ↓
A04.4 structural/static-domain validation
        ↓
finite numeric sanity
        ↓
A04.5 fault / Enabled lockout
        ↓
A04.5 authority validation
        ↓
apply permitted EXTERNAL commands
        ↓
AltDSS/OpenDSS solve on persistent live context
        ↓
native OpenDSS controls act where configured
        ↓
collect solution/convergence/backend status
        ↓
read required semantic state
        ↓
construct canonical observation Dict
        ↓
read realized actuator state where exposed
        ↓
construct RuntimeStepContext
        ↓
reward / termination / truncation hooks
        ↓
emit recorder/runtime information
        ↓
return obs, reward, terminated, truncated, info
```

## 8. Static fault authority

Static faults are established once during initialization and remain plant authority during iteration. Neither native logic nor external action may clear them through normal action channels. Failure to maintain required disabled state is explicit runtime failure.

## 9. Non-convergence semantics

A structured AltDSS/OpenDSS result with `converged=False` is recorded as an outcome. It does not retroactively make an otherwise valid controller action invalid. Hook logic may interpret convergence status if configured. Backend crashes or unreadable required outputs are separate runtime/backend errors.

## 10. Strict observation reads

Every required observation channel must produce the declared path, shape, dtype/type, and semantic value. No silent zero, NaN, stale value, omitted key, or arbitrary default substitution is permitted.

## 11. Requested / applied / realized separation

Runtime preserves canonical requested action, applied/non-applied status and reason, applied action information, and realized actuator/device state where the backend exposes it. Unavailable realized quantities are explicitly unavailable rather than fabricated.

## 12. RuntimeStepContext

Reward, termination, and truncation share a common read-only semantic context:

```python
reward(context: RuntimeStepContext) -> float
termination(context: RuntimeStepContext) -> bool
truncation(context: RuntimeStepContext) -> bool
```

The context may contain canonical controller-visible observation, requested/applied/realized action information, internal semantic state needed for plant/problem evaluation, disturbances/parameters where available, fault/availability state, authority state, OpenDSS solution/convergence/backend status, step index, and explicitly required previous-step context.

It never substitutes controller-side flattened/normalized/tensorized representations.

## 13. Default hooks

Absent custom ProblemSpec hooks:

```text
reward      = 0.0
termination = False
truncation  = False
```

A05 may later define temporal/time-limit truncation.

## 14. Custom hooks through ProblemSpec

ProblemSpec may provide custom reward, termination, and truncation callables. They are invoked by the plant through the same abstract hook boundary as defaults.

Custom hooks:
- receive `RuntimeStepContext`;
- are read-only with respect to plant mutation;
- do not issue actions or change faults/authority;
- return a finite scalar reward or boolean termination/truncation.

Exceptions, invalid types, or non-finite reward fail explicitly.

## 15. Callable provenance

Qualified production custom hooks use stable reproducible callable identity, preferably importable top-level functions. Provenance records module, qualified name, configuration identity, and source/code identity where practical. Arbitrary callable pickling is not required.

## 16. `info` boundary

`info` carries authoritative runtime/audit information such as convergence/backend status, requested/applied/realized audit data, fault/authority state, hook outcomes, identities, and recorder status. It is not a hidden observation channel for scientific controllers.

## 17. Runtime recording surface

A04.7 exposes sufficient runtime information to the existing recorder/history architecture for later metric computation, debugging, analysis, visualization, and reproducibility.

Depending on configured retention detail, recordable data may include:
- canonical observations;
- canonical requested actions;
- applied action/status and reasons;
- realized actuator/device state where available;
- internal semantic state;
- disturbances/parameters;
- fault/availability state;
- authority state;
- solution/convergence/backend status;
- reward/termination/truncation;
- runtime identities;
- step index and later A05 time identity.

A04.7 does not replace the existing recorder architecture. Existing separation of retention detail from execution instrumentation remains authoritative; conceptually basic/intermediate/high detail are implemented through that established policy rather than a competing taxonomy.

## 18. Runtime binding identity

A deterministic `runtime_binding_sha256` identifies the executable A04 boundary and includes resolved-problem, circuit/registry, observation/action-space, reader/writer, authority, static-fault, and hook identities.

Controller-internal algorithm logic that does not change the plant/problem boundary is not part of this hash.

## 19. One-time preflight before production runs

Checks that can be established before iterative simulation are front-loaded into preflight, including circuit/problem/registry identities, compiled spaces, reader/writer availability, native/external ownership capability, native-control suppression capability, static-fault binding capability, hook binding/return contracts, backend capability, and runtime-binding identity.

These checks are not redundantly repeated inside every control step.

## 20. Persistent preflight qualification record

A successful preflight PASS is stored in secondary memory as a machine-readable record whose identity includes all dependencies that can invalidate the A04 executable boundary, including source/runtime identity, backend version, circuit/inventory, A03 registries, resolved problem, spaces, runtime binding, hook identities, and relevant schema/configuration versions.

## 21. Reuse of preflight results

If only controller-internal logic changes while the OpenDSSSim plant/problem/runtime boundary remains byte/identity-equivalent, the existing preflight PASS may be reused after verifying its cache identity.

If any covered dependency changes, the record is invalid for that boundary and relevant checks run again.

This does not replace controller-specific qualification.

## 22. Behavioral qualification matrix

Eventual A04 implementation qualification must cover at least:
- `problem=None` / native-only operation;
- default and custom reward/termination/truncation hooks;
- invalid custom hook returns/exceptions;
- NATIVE, EXTERNAL, and valid HYBRID authority;
- authority conflict rejection;
- static fault -> qualified `Enabled=False`;
- faulted action channel remains structurally present but is not applied;
- invalid Gym and non-finite action rejection;
- wrong-circuit/runtime-binding rejection;
- required-observation read failure;
- structured non-convergence recorded without automatic action condemnation;
- deterministic one-time initialization;
- persistent same-context iterative stepping;
- requested/applied/realized audit separation;
- recorder surface at configured retention detail;
- stable runtime-binding hash;
- persistent preflight record creation;
- valid cache reuse when only controller-internal logic changes;
- preflight invalidation when a covered boundary identity changes;
- absence of plant-side derived-observation/wrapper infrastructure;
- preservation of A01–A04.6 behavior.

Backend-dependent behavior uses genuine AltDSS/OpenDSS execution where practical.

## 23. Step-dependent checks only during iteration

Normal step logic repeats only checks that are inherently step-dependent: current Gym action validation, finite sanity, current fault/availability lockout, authority permission, command application, solve, current observation reads, hooks, and runtime recording.

## 24. A05 boundary

A04.7 does not define profile indexing, load/PV/weather replay, simulation-clock semantics, forecast horizon/noise, time-varying fault occurrence, repair timing, event schedules, episode duration, or time-limit policy. Those are A05 responsibilities.

## 25. Post-A04 workflow

After A04.7 documentation qualification:

```text
whole-A04 documentation freeze/qualification
        ↓
fresh repository tree
        ↓
implementation-directed evidence bundle
        ↓
freeze REUSE / ADAPT / NEW / IMMUTABLE source plan
        ↓
A04 runtime implementation
        ↓
independent behavioral qualification
```

## 26. Ratification decision

A04.7 is RATIFIED with these binding principles:

1. Runtime binds an already-resolved problem; it does not rediscover semantics.
2. ProblemRuntimeBinding is immutable execution infrastructure.
3. Binding is strict and atomic.
4. Circuit/registry/problem/space identities are verified once before the iterative loop.
5. Baseline compile/restore, binding, authority configuration, and static-fault application occur once before the first iteration, not every step.
6. Iteration continues on the same live evolving AltDSS/OpenDSS context.
7. Explicit new reset/episode may intentionally reinitialize the baseline.
8. Reset returns canonical observation + info.
9. Step follows A04.4/A04.5 -> AltDSS solve -> semantic read -> hooks -> recorder.
10. Static fault authority remains enforced throughout iteration.
11. Structured non-convergence is recorded and is not automatically action invalidity.
12. Required observation reads fail closed.
13. Requested/applied/realized action data remain distinct and auditable.
14. Reward/termination/truncation share a read-only RuntimeStepContext.
15. Neutral defaults are `0.0`, `False`, `False`.
16. ProblemSpec may supply custom plant-invoked hooks.
17. Custom hooks are strictly typed, read-only, and provenance-bearing.
18. `info` is audit/runtime information, not hidden controller observation.
19. Runtime exposes sufficient data to the existing configurable recorder/history system for later metrics and visualization.
20. `runtime_binding_sha256` identifies the executable A04 plant/problem boundary.
21. Pre-run checks that can happen once are front-loaded into preflight.
22. Successful preflight qualification is persisted in secondary memory.
23. A valid preflight PASS may be reused when only controller-internal logic changes and the OpenDSSSim boundary is unchanged.
24. Covered boundary changes invalidate cached preflight.
25. Runtime repeats only genuinely step-dependent checks.
26. A04 implementation qualification must exercise the behavioral matrix above.
27. A05 owns temporal/profile/forecast/event semantics.
28. Whole-A04 documentation freeze/qualification occurs before source implementation.
29. This document alone does not authorize A04 runtime source implementation.
