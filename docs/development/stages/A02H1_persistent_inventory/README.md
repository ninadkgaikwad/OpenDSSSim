# A02H1 — Persistent Circuit Inventory + Native Control Discovery

**Status:** FINAL/FROZEN  
**Qualified patch:** `OpenDSSSim_A02H1_Persistent_Circuit_Inventory_Native_Control_Discovery_v01R1_20261008`

## Responsibility

A02H1 converts repeated static A02 discovery into a persistent circuit-compilation artifact
and explicitly records native OpenDSS control/protection relationships.

A02H1 answers:

> **What physically exists, and can that static physical description be safely reused?**

## Persistent `CircuitInventory`

The inventory stores static facts including:

- schema/backend/engine identity;
- master/source-tree identity and dependency manifest;
- buses/nodes;
- DSS classes and object identities;
- circuit-element structure;
- native control/protection objects;
- controller-to-controlled/monitored/switched/protected relationships.

It intentionally excludes live episode truth such as voltages, currents, powers,
convergence, live tap positions, switch realization, capacitor realization, SOC, and
controller queue behavior.

## Whole-source identity

Inventory validity is tied to a conservative source-tree fingerprint rather than only
`Master.dss`. A dependent DSS/CSV/data-file change must invalidate the cached inventory.

## Native control relationships

A02H1 recognizes the frozen control-element catalog and roles such as:

```text
CONTROLS
MONITORS
MONITORS_BUS
SWITCHES
PROTECTS
COORDINATES_CONTROL
```

Examples include:

```text
RegControl -> Transformer/AutoTrans
CapControl -> monitored Element + controlled Capacitor
SwtControl -> switched circuit element
Relay/Recloser/Fuse -> monitored/protected element
```

The existence of a native controller does **not** grant external OpenDSSSim action
authority.

## Runtime reuse

A valid persisted inventory is loaded across episodes/environments without rerunning A02
static discovery. Explicit A02 live-discovery APIs remain available when intentionally
requested.

## Deferred

A02H1 does not decide:

- whether a discovered quantity is state/action/disturbance/constraint/parameter;
- external vs native control authority;
- `ProblemSpec`;
- final Gym spaces;
- time-series execution.

Those decisions begin at A03+.

## Authoritative records

- architecture contract:
  `docs/development/architecture/OpenDSSSim_A02H1_Persistent_Circuit_Inventory_Native_Control_Discovery_Contract_v01R1_20261008.md`
- patch:
  `docs/development/patches/OpenDSSSim_A02H1_Persistent_Circuit_Inventory_Native_Control_Discovery_v01R1_20261008.md`
