# A02 — Generalized Engine + Circuit Capability Discovery

**Status:** FINAL/FROZEN  
**Qualified patch:** `OpenDSSSim_A02_Generalized_Engine_Circuit_Capability_Discovery_v01R1_20261007`

## Responsibility

A02 makes the loaded circuit inspectable in a generalized, deterministic, read-only form.

It discovers:

- engine/backend identity and feature surface;
- buses and node names;
- instantiated DSS classes and native full object names;
- complete one-time native property snapshots;
- circuit-element structure: phases, terminals, conductors, node order/reference, bus specs;
- topology summary;
- deterministic discovery semantic SHA256.

## Core rule

A02 answers:

> **What physically exists in this loaded OpenDSS circuit?**

It does not decide what a property means to a controller or simulator semantic layer.

## Native vocabulary

Native OpenDSS object identities remain canonical, e.g.:

```text
PVSystem.PV1
Transformer.Reg1
Capacitor.Cap1
Line.L1
RegControl.RC1
```

## Read-only contract

Discovery must not mutate the circuit. A writable AltDSS property is not treated as an
OpenDSSSim action merely because the API exposes a setter.

## Determinism

Repeated discovery of the same loaded circuit and independent equivalent contexts must
produce semantically equivalent discovery output.

## Deferred

A02 does not implement:

- persistent inventory reuse;
- semantic mutability classification;
- action/state/disturbance/constraint/parameter registries;
- `ProblemSpec`;
- controllers.

## Authoritative records

- architecture contract:
  `docs/development/architecture/OpenDSSSim_A02_Generalized_Engine_Circuit_Capability_Discovery_Contract_v01_20261006.md`
- patch:
  `docs/development/patches/OpenDSSSim_A02_Generalized_Engine_Circuit_Capability_Discovery_v01R1_20261007.md`
