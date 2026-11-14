# Controller Capability Requirements

**Status:** C0A scaffold

## Principle

Compatibility is explicit and machine-checkable. A controller is generalized by
declaring the capabilities it requires and binding to discovered compatible objects,
not by pretending all circuits support all controls.

## Requirement categories

1. observation capabilities;
2. action capabilities;
3. topology/model-service capabilities;
4. forecast capabilities;
5. physical/operational constraint capabilities;
6. algorithm/runtime capabilities.

## Initial P1 concepts to audit

Potential requirements include:
- bus/node voltage observations;
- converged snapshot solution;
- one or more externally controllable voltage/VAR resources;
- regulator/tap, capacitor, DER/inverter reactive power, or storage controls as selected
  by the frozen P1 benchmark;
- forecasts if required by the selected MPC formulation.

Exact device requirements are **not frozen in C0A**.

## Initial P2 concepts to audit

Potential requirements include:
- topology graph;
- source/connectivity information;
- switchable branches;
- load/bus information;
- fault/outage/event description;
- feasibility checks;
- DER support actions if included in the common P2 problem.

Exact requirements are **not frozen in C0A**.

## Unsupported semantics

The later implementation must report:
- controller identifier;
- circuit/problem identifier;
- missing requirement identifiers;
- optional diagnostic explanation;
- status `UNSUPPORTED`.

No silent degradation or substitution is permitted.
