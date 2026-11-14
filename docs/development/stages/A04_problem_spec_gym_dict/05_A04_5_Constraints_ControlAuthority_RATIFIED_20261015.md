# A04.5 - Constraints, Fault Availability, and Control Authority

**Date ratified:** 2026-10-15  
**Status:** RATIFIED  
**Runtime implementation authorized by this document:** No

## Purpose

A04.5 defines action admissibility and control ownership without turning OpenDSSSim into a second electrical-feasibility engine.

The binding design is:

```text
OpenDSSSim exposes qualified action channels.
A04.4 validates canonical Gym structure/static domain.
A04.5 enforces finite input sanity, fault/device availability, and ownership.
AltDSS/OpenDSS remains authoritative for native network/device physics and solve behavior.
```

## OpenDSS-Authoritative Feasibility Boundary

A04.5 does not independently duplicate or police:

- inverter capability circles;
- voltage operating bands;
- thermal limits;
- nonlinear power-flow feasibility;
- detailed tap/device physics;
- topology electrical feasibility;
- native protection/control equations;
- other OpenDSS-internal operating logic.

After A04.4 Gym validity, A04.5 performs no additional numerical band/set feasibility engine beyond rejecting non-finite numeric commands (`NaN`, `+/-Inf`) and enforcing availability/ownership.

Permitted commands are passed to AltDSS/OpenDSS. OpenDSSSim records authoritative solve/convergence/status and required realized outputs/metrics.

## Narrow A04.5 Admissibility Contract

A selected external channel is admissible to apply when:

1. its canonical action passes the already-ratified A04.4 Gym contract;
2. the supplied numeric value is finite where numeric;
3. its target device is not fault-disabled;
4. the channel is externally owned under the resolved authority contract.

A04.5 does not add an independent electrical-feasibility inequality layer.

## ProblemSpec Fault Association

`ProblemSpec` contains explicit generalized fault association.

A fault may target **any OpenDSS device/element** whose qualified backend/A03 semantics support availability through `Enabled`.

Targets may be authored by exact semantic reference, semantic query, or a resolved named/ordered group.

Resolution binds fault declarations to exact device identities. A target without qualified availability/`Enabled` semantics fails closed.

## Faulted Device Semantics

A fault does not delete a target from the circuit or semantic registries.

Conceptually:

```text
device exists        = TRUE
fault active         = TRUE
Enabled              = FALSE
controller available = FALSE
```

The device remains semantically identifiable and may still appear in selected observations/state/topology metadata.

The actual electrical behavior of `Enabled=False` is delegated to qualified AltDSS/OpenDSS behavior for the device class.

## Fault Lockout

While a fault is active:

- the device is forced `Enabled=False`;
- its normally selected action channels remain structurally present in the static Gym action space;
- external controller commands for that device are not applied;
- native controller logic is not permitted to re-enable or actuate the disabled target;
- ordinary controller action channels cannot clear the fault or set `Enabled=True`.

Fault/device-disabled lockout has higher precedence than NATIVE, EXTERNAL, or HYBRID ownership.

## Fault Clearing

Fault clearing is not an ordinary controller action.

Static fault application belongs to A04.5.

Time-varying fault/repair events are deferred to A05 and must reuse this same fault-lockout contract.

## Static Gym Structure Under Faults

Faults do not mutate `action_space` or `observation_space`.

A normally selected channel remains structurally present even while disabled.

A controller may therefore structurally supply a value for the locked-out channel, but the runtime records that it was not applied because the device was fault-disabled.

This is explicit lockout, not implicit hold/default behavior.

## Requested, Applied, and Realized

A04.5 preserves:

\[
u_t^{req}\rightarrow u_t^{app}\rightarrow u_t^{real}.
\]

At minimum, runtime auditability distinguishes:

- requested value;
- admissible/not-admissible-to-apply status;
- whether a command was applied;
- machine-readable reason when not applied;
- post-solve realized state/value where exposed by the backend.

Example:

```text
requested_value = <controller value>
admissible      = false
applied         = false
reason          = FAULT_DISABLED
realized        = post-solve/native device state
```

## No Silent Command Modification

A04.5 does not silently clip, project, rescue, substitute, reinterpret, or replace an external controller command.

For an available, externally owned, finite, Gym-valid channel, the requested command is the command passed toward the backend.

Any future projection policy would require separate ratification and explicit requested-versus-applied provenance.

## Authority Is Resolved on Actuator Channels

Authority is attached to actual actuator/action channels, not merely to native controller-object names.

Example:

```text
RegControl.R1
    -> manipulates
Transformer.Reg1.tap
```

The ownership decision is about `Transformer.Reg1.tap`.

## NATIVE Authority

For a channel resolved as `NATIVE`:

- its associated native OpenDSS control is configured at initialization/reset;
- native OpenDSS logic owns that actuator during the solve;
- the external controller does not own that channel;
- runtime external commands to that native-owned actuator are not permitted;
- realized actuator state may still be observed.

The ProblemSpec establishes native-controller setup once for the episode.

Ordinary runtime actions may not:
- enable/disable native controllers;
- retune native-control configuration;
- change native/external ownership;
- alter the HYBRID partition.

A different native-control setup requires a new ProblemSpec/reset/scenario configuration.

## EXTERNAL Authority

For an `EXTERNAL` channel:

- the selected external controller exclusively owns that actuator;
- competing native actuation of that exact actuator must be disabled/suspended/configured out at initialization;
- native control objects may remain semantically present;
- simultaneous native and external writes to the same actuator are prohibited.

If exclusive ownership cannot be guaranteed, runtime binding fails closed.

## HYBRID Authority

`HYBRID` means an explicit **non-overlapping partition** of actuator ownership.

\[
\mathcal U
=
\mathcal U_{\mathrm{native}}
\;\dot\cup\;
\mathcal U_{\mathrm{external}}.
\]

Example:

```text
Native:
    regulator taps
    capacitor switching

External:
    PV inverter kvar
```

A04.5 does not permit simultaneous native and external ownership of the exact same actuator.

Any future co-control/arbitration policy would require separate ratification.

## Authority Conflicts Fail Closed

Invalid examples include:

- external action selected while the same channel is declared NATIVE;
- overlapping NATIVE/EXTERNAL declarations;
- EXTERNAL ownership where competing native actuation cannot be disabled;
- overlapping HYBRID partitions.

These fail before normal stepping.

## Fault Lockout Overrides Authority

Precedence is:

```text
FAULT / DEVICE DISABLED
        >
CONTROL AUTHORITY
        >
ordinary command application
```

A fault-disabled target is unavailable regardless of whether its normal ownership is NATIVE or EXTERNAL.

## Reset Ordering

Reset deterministically reconstructs the episode:

```text
restore/recompile baseline feeder
        |
        v
bind resolved ProblemSpec
        |
        v
configure NATIVE / EXTERNAL / HYBRID ownership
        |
        v
apply static ProblemSpec fault set
        |
        v
faulted targets -> Enabled=False
        |
        v
apply initial exogenous state
        |
        v
AltDSS/OpenDSS solve
        |
        v
read solution/status/state
        |
        v
construct canonical observation Dict
```

Faults and authority configuration from a prior episode may not leak into a new reset.

## Controller Visibility

Fault/availability/authority information exists in the environment's internal semantic context but is not automatically controller-visible.

A04.2 continues to decide whether a particular ProblemSpec exposes fault status, availability, switch/topology state, or authority information to the controller.

## Post-Solve Responsibility

After permitted commands are passed to OpenDSS and the solve runs, OpenDSSSim records authoritative outputs needed by the environment/problem, including as applicable:

- solve success/failure;
- convergence/status;
- backend/solution errors;
- required realized state/control values;
- problem-selected metrics.

A04.5 does not construct a parallel electrical-constraint violation engine.

## Machine-Readable Action Status

Action application requires deterministic machine-readable status/reason information.

Minimum conceptual reasons include:

```text
ADMISSIBLE_APPLIED
FAULT_DISABLED
AUTHORITY_NATIVE
INVALID_GYM_ACTION
NONFINITE_ACTION
BACKEND_APPLICATION_ERROR
```

Exact enum names are implementation-detail scope.

A04.5 intentionally does not add generic statuses for electrical constraints that OpenDSS itself owns.

## Canonical Step Boundary

```text
requested semantic action Dict
          |
          v
A04.4 Gym validation
          |
          v
finite-value sanity
          |
          v
fault / Enabled lockout
          |
          v
control-authority validation
          |
          v
applied command record
          |
          v
AltDSS/OpenDSS command application + solve
          |
          v
solution / convergence / status
          |
          v
realized state/action
          |
          v
problem-selected metrics + reward / termination / truncation
```

## Ratification Decision

A04.5 is RATIFIED with these binding principles:

1. OpenDSSSim does not become a second electrical-feasibility engine.
2. A04.4 Gym validity remains the static action representation/domain gate.
3. A04.5 additionally checks finite numeric input, fault/device availability, and actuator ownership.
4. ProblemSpec supports generalized fault association for any qualified OpenDSS device/element.
5. Faulted devices remain semantically present and are forced `Enabled=False`.
6. Fault-disabled devices' selected action channels remain structurally present but are not applied.
7. Normal controller actions cannot clear faults or re-enable faulted devices.
8. Fault lockout overrides NATIVE, EXTERNAL, and HYBRID ownership.
9. Requested, applied, and realized values/states remain distinguishable.
10. No silent clipping, projection, rescue, substitution, or reinterpretation is allowed.
11. Authority is resolved on actual actuator/action channels.
12. NATIVE ownership means native OpenDSS control owns the actuator and external runtime control is prohibited.
13. Native-control setup is established by ProblemSpec/reset and is immutable during ordinary runtime stepping.
14. EXTERNAL ownership means exclusive external ownership and competing native actuation must be disabled/suspended.
15. HYBRID means a disjoint native/external actuator partition, not simultaneous co-control.
16. Authority conflicts fail closed before normal stepping.
17. Reset restores baseline state and deterministically reapplies authority and static faults.
18. Static faults are A04.5 scope; time-varying fault/repair events are deferred to A05.
19. Fault/availability/authority state is internally available but controller visibility remains governed by A04.2.
20. Post-solve A04.5 bookkeeping is limited to authoritative solve/convergence/error/status, required realized values, and problem-selected metrics.
21. Machine-readable application status/reasons are required.
22. No A04 runtime implementation is authorized by this document.
