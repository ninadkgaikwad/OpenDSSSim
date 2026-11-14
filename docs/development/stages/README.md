# OpenDSSSim Development Stage Ledger

## Purpose

This directory is the durable engineering record for staged OpenDSSSim development.
It complements:

- `docs/development/architecture/` — frozen architecture contracts and cross-stage invariants;
- `docs/development/patches/` — immutable implementation/qualification history;
- `docs/development/control_science/` — controller-science requirements maintained independently.

A stage record explains **what a stage owns, why the boundary exists, what it consumes,
what it produces, what is explicitly deferred, and how it is qualified**.

## Development rule

For every substantial simulator stage:

1. freeze the predecessor repository identity;
2. ratify the stage contract before source implementation;
3. document scope, semantics, persistence/runtime behavior, and qualification;
4. install through an auditable patch;
5. qualify predecessor preservation and successor behavior;
6. mark the stage `FINAL/FROZEN` only after independent qualification.

Patch records are not substitutes for stage design documentation.

## Current stage ledger

| Stage | Responsibility | Status |
|---|---|---|
| A00 | Architecture baseline and reuse/adapt/new planning | FROZEN |
| A01 | AltDSS context ownership, circuit loading, snapshot solve, minimal Gym lifecycle | FINAL/FROZEN |
| A01D1 | Simulator/controller architectural split and parallel-development policy | FINAL/FROZEN |
| A02 | Generalized read-only engine/circuit capability discovery | FINAL/FROZEN |
| A02H1 | Persistent `CircuitInventory` and native OpenDSS control/protection relationships | FINAL/FROZEN |
| A03D1 | A03 semantic-registry documentation freeze | IN QUALIFICATION |
| A03 | Persistent seven semantic registries | PLANNED AFTER A03D1 |
| A04 | `ProblemSpec`, selected observation/action surfaces, compatibility integration | PLANNED |
| A05 | Exogenous disturbance/forecast execution and episode-time progression | PLANNED |

## Cross-stage semantic boundary

```text
A02/A02H1
    What physically exists?

A03
    What does each available quantity/capability mean to OpenDSSSim?

A04
    What does a particular control problem expose/use?

A05+
    How do time-varying disturbances, forecasts, actions, and controller workflows execute?
```

## Native vocabulary

OpenDSS classes/properties and native electrical vocabulary remain canonical wherever
possible. OpenDSSSim may add semantic metadata and typed service addresses, but must not
replace the distribution-system representation with paper-specific names.

## Controller boundary

Controller-science requirements can request simulator capabilities, but controllers never
mutate AltDSS directly. Only the simulator plant boundary owns physical mutation.
