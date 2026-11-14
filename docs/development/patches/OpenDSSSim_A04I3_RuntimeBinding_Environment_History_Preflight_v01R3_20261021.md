# OpenDSSSim A04I3 — Runtime Binding + Environment + History + Preflight

**Patch ID:** `OpenDSSSim_A04I3_RuntimeBinding_Environment_History_Preflight_v01R3_20261021`  
**Date:** 2026-10-21  
**Predecessor:** Qualified A04I2, 173 files  
**Predecessor qualified source-manifest SHA256:** `EFF9B4A076560570D8DF984F20202FADCE2D867FE45E7FAA7237DA76934D5F89`

## Purpose

A04I3 integrates the qualified A04I1 problem contract/Gym spaces and A04I2 semantic runtime-access layer into the generalized Gymnasium plant. It implements immutable runtime binding, one-time reset initialization, persistent same-context stepping, NATIVE/EXTERNAL/HYBRID authority, static faults, requested/applied/realized audit, runtime hooks, H0-H3 history, and persistent preflight.

The A05 temporal/profile/forecast boundary remains unchanged and is not implemented here.

## V01R3 fresh-rebuild corrections

V01R3 is rebuilt from the exact qualified 173-file A04I2 authority. V01R1 and V01R2 remain unqualified attempts and are not predecessor states.

V01R2 established that the earlier source-layout import defect was resolved by a temporary process-local `PYTHONPATH=<RepoRoot>\src;<RepoRoot>`. Its targeted tests then exposed two independent test/contract issues.

### 1. Canonical Gym action keys

The A04I1 Gym `Dict` contract is exact: controller keys must match the compiled semantic action paths. V01R2 tests hard-coded literal action keys instead of deriving the exact compiled paths, and genuine AltDSS execution showed those literals did not satisfy `action_space.contains(...)`. V01R3 tests and standalone validation therefore build test actions from the immutable `ProblemRuntimeBinding.action_bindings[*].path`.

This does **not** add case-folding, aliases, wrappers, or hidden action canonicalization to the plant. Controller actions must still match the compiled canonical semantic `Dict` exactly.

### 2. A02H1 `SWITCHES` versus frozen A04 `CONTROLS` authority evidence

A02H1 records the physical relation `SwtControl -> SwitchedObj` with role `SWITCHES`. The frozen A04 authority rule permits only relationship role `CONTROLS` to establish native actuator ownership/suppression; `MONITORS` and `PROTECTS` are non-owning, and A04I3 does not silently reinterpret another role as `CONTROLS`.

Therefore an externally owned actuator targeted by an A02H1 `SWITCHES` relationship cannot currently prove exclusive external ownership from the frozen metadata vocabulary. V01R3 fails such a binding closed with `RuntimeBindingError` instead of leaving a competing native switch controller enabled.

HYBRID qualification is exercised with a contract-supported `RegControl -> Transformer` `CONTROLS` relationship while independently preserving native `CapControl -> Capacitor` ownership. Static fault lockout is exercised on a PVSystem so the fault test does not depend on the unresolved `SWITCHES` vocabulary.

This preserves A02H1/A03/A04I1/A04I2 source byte identity. Any future decision to normalize A02H1 `SWITCHES` into the A04 ownership vocabulary requires an explicit predecessor compatibility revision; it is not hidden inside A04I3.

## Runtime lifecycle

For non-null `ProblemSpec`, construction compiles the static feeder/A03 authority once so Gym spaces are available before reset, but does not issue controller writes or solve. First reset verifies binding identity, suppresses qualified competing native `CONTROLS` sources, applies static faults (`Enabled=False`), solves, reads the canonical observation, and creates the initial context/history record. Ordinary steps validate the exact Gym action, perform finite checks, enforce fault/authority precedence, apply semantic writes, solve the same live backend context, read realized state, build `RuntimeStepContext`, invoke hooks, and append history. Explicit later reset recompiles/restores the baseline in the same owned backend context and reapplies static configuration.

## Authority policy

Precedence remains:

```text
FAULT / DISABLED
    >
CONTROL AUTHORITY
    >
COMMAND APPLICATION
```

Only A02H1 `role == CONTROLS` may establish suppression. EXTERNAL is exclusive and fails closed when exclusivity cannot be proven. HYBRID is a disjoint partition. No same-actuator co-control is introduced.

## Action audit

The status vocabulary remains exactly:

- `ADMISSIBLE_APPLIED`
- `FAULT_DISABLED`
- `AUTHORITY_NATIVE`
- `INVALID_GYM_ACTION`
- `NONFINITE_ACTION`
- `BACKEND_APPLICATION_ERROR`

OpenDSSSim does not add electrical-feasibility status codes or silently clip/project/rescue/substitute controller commands.

## Hooks, history, and preflight

Default hooks remain reward `0.0`, termination `False`, truncation `False`. Imported hooks receive read-only `RuntimeStepContext` and fail explicitly on exceptions/bad return types/nonfinite reward.

History retention H0/H1/H2/H3 remains independent of execution instrumentation FAST/STANDARD/AUDIT. Persistent A04 preflight is keyed by implementation/runtime/circuit/A03/problem/space/binding/hook identities and may be reused only when that boundary is unchanged.

## Preservation

V01R3 intentionally preserves byte identity for:

- A03 semantic schema/compiler/policy;
- A04I1 problem resolution/Gym-space compilation;
- A04I2 backend and `runtime/access.py`;
- A02H1 relationship discovery.

The only predecessor integration file revised outside newly added A04I3 modules remains `plant/core.py`, adding the no-solve `prepare_reset()` primitive required to configure authority/faults before the first authoritative solve.

## Successor

After independent A04I3 qualification, proceed to **A04I4 — Full Behavioral Qualification + A04 Implementation Freeze**.
