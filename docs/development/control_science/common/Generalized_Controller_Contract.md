# Generalized Controller Contract

**Status:** C0A scaffold — final typed Python contract deferred until C4

## Conceptual types

### ControllerRequirements

Declares what must exist before a controller can instantiate:

- required observation capabilities;
- required action capabilities;
- topology/model-service needs;
- forecast requirements;
- constraint requirements;
- optional algorithm-specific requirements.

### ControllerContext

Read-only controller-facing context:

- `ProblemSpec`;
- current observation;
- authorized state view;
- forecast view;
- capability/registry metadata;
- non-mutating topology/model services;
- episode/time metadata.

### ControllerOutput

Controller result:

- requested action `a_req`;
- diagnostics;
- solver/policy metadata;
- provenance.

The controller never supplies `a_applied` or `a_realized`.

## Compatibility semantics

A controller instantiation must resolve to exactly one of:

- `SUPPORTED`;
- `UNSUPPORTED` with machine-readable missing requirements.

Silent feature substitution is forbidden.

## Generalization rule

Generalized source code:
- does not hard-code IEEE-123 object names;
- binds to discovered native objects through registry/problem selections;
- validates capability requirements before operation;
- preserves native OpenDSS vocabulary wherever practical.

Paper-specific object identities and benchmark selections are configuration, not source
logic.

## Deferred implementation

No Python classes are frozen by this file. Exact dataclasses/protocols/ABCs will be
defined in C4 after P1 and P2 science contracts are frozen and the simulator A03/A04
surface is known.
