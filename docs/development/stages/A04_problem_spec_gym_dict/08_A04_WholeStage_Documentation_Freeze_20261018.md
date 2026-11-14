# A04 Whole-Stage Documentation Freeze

**Date:** 2026-10-18  
**Stage:** A04 - ProblemSpec + problem-specific Gymnasium Dict spaces  
**Status:** DOCUMENTATION FROZEN PENDING INDEPENDENT QUALIFICATION  
**Runtime/source implementation authorized:** No

## 1. Purpose

Freeze the complete ratified A04 design before any A04 runtime source implementation begins. A04.1 through A04.7 have each been ratified, documented, installed, and qualified.

## 2. Authoritative predecessor

```text
Repository files: 151
Qualified source-manifest SHA256:
7C53C591D68C32818F16905D4AFCBD12601FAC2B37EBD0696ACEBFF83E849A96
```

All 151 predecessor files must remain byte-for-byte unchanged by this documentation-only freeze patch.

## 3. Frozen cross-stage architecture

```text
CircuitInventory + A03 SemanticRegistryBundle
        -> ProblemSpec
        -> strict semantic resolution
        -> ResolvedProblemSpec
        -> A04.4 canonical nested Gymnasium Dict spaces
        -> immutable ProblemRuntimeBinding
        -> one-time run/episode initialization
        -> persistent live AltDSS/OpenDSS iterative context
```

OpenDSSSim remains the semantic plant. Controller-specific feature engineering, flattening, normalization, tensorization, MPC vector construction, RL preprocessing, and controller-specific action encoding remain controller-side responsibilities.

## 4. Frozen subsection authorities

### A04.1 - ProblemSpec Core Contract
Authored `ProblemSpec` is distinct from exact `ResolvedProblemSpec`; semantic resolution is strict/fail-closed; native quantities resolve through A03; `problem=None` remains valid; ProblemSpec can narrow but not enlarge plant capability; NATIVE/EXTERNAL/HYBRID authority and default/custom plant hooks are first-class.

### A04.2 - Observation / State Selection
Controller observation is an explicit selected view, not all A03 state. Canonical nested semantic Dict paths preserve OpenDSS identity. No automatic hidden-state leakage. Future forecast quantities are an A05 service.

### A04.3 - Action Selection
Only qualified A03 ActionRegistry channels become controller actions. Writable properties are not automatically actions. Requested/applied/realized are distinct. No silent clipping, rescue, substitution, or reinterpretation.

### A04.4 - Gymnasium Dict-Space Compilation
ResolvedProblemSpec is the semantic input. Observation/action spaces are deterministic nested Dict spaces with fixed shapes and explicit domains. Spaces are immutable during an episode. Runtime values must satisfy the compiled space contracts.

### A04.5 - Fault Availability and Control Authority
OpenDSSSim does not duplicate OpenDSS electrical-feasibility logic. A04.5 checks finite input, fault/device availability, and actuator ownership. Faulted devices remain semantically present and are forced `Enabled=False`. NATIVE is native-owned, EXTERNAL is exclusive external ownership, HYBRID is a disjoint partition.

### A04.6 - Controller-Side Transformation Boundary
OpenDSSSim v1 does not implement derived controller observations, generic observation wrappers, or generic action wrappers. Controller preprocessing stays with RBC/MPC/RL. Reward/termination/truncation remain plant invocation hooks with neutral defaults and optional ProblemSpec-supplied custom callables.

### A04.7 - Runtime Binding, One-Time Preflight, and Qualification
Runtime binds an already-resolved problem. Compile/restore, identity verification, ProblemRuntimeBinding establishment, authority configuration, and static fault application happen once before the first iterative step. Later steps continue on the same live evolving AltDSS/OpenDSS context. Runtime exposes sufficient audit data to the existing recorder/history architecture. Pre-run checks are front-loaded and successful qualification is persisted in secondary memory for safe reuse when the OpenDSSSim plant/problem/runtime boundary is unchanged.

## 5. Explicit A04 non-goals

A04 does not own profile replay/time indexing, forecast generation/noise, episode-clock semantics, time-varying fault/repair event schedules, controller preprocessing, MPC/RL/rule-controller science, or a duplicate OpenDSS feasibility engine.

## 6. Whole-stage qualification gate

Whole-A04 documentation qualification must prove: exact 151-file predecessor identity; all predecessor files preserved byte-for-byte; A04.1-A04.7 documentation presence; cross-stage invariants represented; no new runtime Python source; deterministic post-freeze source manifest.

## 7. Required workflow after freeze

```text
whole-A04 documentation qualification
    -> fresh repository tree
    -> implementation-directed evidence bundle
    -> inspect actual A01/A02/A03/A04-adjacent source
    -> freeze REUSE / ADAPT / NEW / IMMUTABLE implementation matrix
    -> freeze exact A04 source patch + tests
    -> implement A04 runtime
    -> unit/integration/genuine AltDSS qualification
    -> A04 implementation freeze
    -> A05 design ratification/documentation
```

This whole-stage freeze does not authorize A04 source implementation.
