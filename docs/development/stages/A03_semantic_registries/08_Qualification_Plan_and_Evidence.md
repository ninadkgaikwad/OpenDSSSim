# A03.8 — Qualification Plan and Evidence

**Status:** PLAN FROZEN; implementation evidence pending.

## 1. Predecessor integrity

A03 implementation must start from the independently qualified A03D1 documentation
predecessor and preserve:

- A01/A02/A02H1 behavior;
- controller-science files byte-for-byte unless an explicitly separate controller patch
  changes them;
- documentation contract identity.

## 2. Schema qualification

Tests must prove:

- all three semantic address families serialize deterministically;
- all four mutability classes are supported;
- canonical semantic IDs are deterministic;
- all seven registries serialize inside one bundle;
- equivalent inputs/policy yield identical semantic SHA256.

## 3. No writable-property heuristic

Tests must explicitly prove that unrelated writable properties do not become
`STEP_CONTROLLABLE`.

Representative exclusions should include electrical/configuration properties that are
writable in AltDSS but are not legitimate normal time-step control actions.

## 4. Class-policy qualification

Representative tests must cover at minimum:

- `Load`;
- `PVSystem`;
- `Storage`;
- `Capacitor`;
- `Transformer`/`AutoTrans`;
- switchable `Line`/circuit element;
- `Generator`;
- `Bus`;
- `Solution`;
- native controller/protection objects.

Tests should verify both positive classifications and explicit exclusions.

## 5. Physical endpoint vs native controller

Qualification must prove distinctions such as:

```text
RegControl configuration != external transformer tap command
CapControl configuration != external capacitor state command
SwtControl configuration != physical branch command endpoint
```

## 6. Runtime-readout qualification

Tests must show solved/runtime quantities can be represented through
`RuntimeReadoutAddress` without inventing fake DSS properties.

Representative channels should include:

- bus voltage;
- element current/power;
- convergence;
- topology/connectivity where implemented.

## 7. Runtime-command qualification

Tests must show legitimate operation-style actions use `RuntimeCommandAddress` where
appropriate, including generalized switching semantics.

## 8. Disturbance qualification

Tests must distinguish:

```text
STEP_EXOGENOUS
```

from controller action, including representative load P/Q and PV-availability semantics.

No time-series progression is required in A03.

## 9. Constraint boundary qualification

Tests must demonstrate:

- intrinsic device limits can appear in `ConstraintRegistry`;
- P1's problem voltage band is **not** automatically inserted as a global A03 constraint.

## 10. Capability qualification

Tests must prove capabilities derive from actual semantic/circuit evidence and are
machine-queryable.

Absence of a relevant device/capability must not be silently replaced with another device
family.

## 11. Persistence/reuse qualification

A03 must prove:

1. first valid use compiles/persists a semantic bundle;
2. reset in the same environment does not reclassify;
3. a new environment loads/reuses a valid bundle;
4. A02 full discovery is not rerun merely to rebuild semantics;
5. source/inventory change invalidates;
6. schema change invalidates;
7. semantic-policy version/hash change invalidates;
8. corrupted bundle is rejected.

## 12. Static vs dynamic qualification

Persisted bundle must exclude live episode values.

## 13. Regression gates

A03 qualification must include:

- A01 standalone validator PASS;
- A02 standalone validator PASS;
- A02H1 standalone validator PASS;
- full repository pytest PASS;
- environment unchanged.

## 14. Evidence section

After source implementation and independent qualification, this file is updated through a
versioned documentation/implementation patch with:

- patch ID;
- source-manifest SHA256;
- semantic-policy SHA256;
- bundle schema version;
- test counts;
- qualification artifacts;
- final PASS/freeze status.
