# OpenDSSSim A05I6R1 — Canonical Observation Test Repair

**Date:** 2026-11-02 (US Pacific)  
**Type:** Integration-test-only qualification repair; no runtime/backend/controller changes.

## Predecessor and failure provenance

This amendment applies only to the **installed but unqualified A05I6** source manifest (241 files), SHA-256
`8F89B42EAA0E0E1D90ACBEAA98FB45E32C00BBCBB9CEDCB18EB3BB5D3FADBE98`.
The original A05I6 qualification evidence (SHA-256 `7737ED74C65676D96DE1B1C488E828BFC41685508809A116C84E413AD54A331B`)
records 95 targeted tests passed, four failures and zero `JSONDecodeError` occurrences. All four failures
are `KeyError: 'measure'` at a newly introduced assertion in
`tests/integration/test_a05i6_ieee123_controller_boundary.py`.

## Root cause and correction

`SelectionGroup('measure', ...)` is an authoring/group-selection label. It is **not** an observation
root in A04. Frozen A04 `compile_gym_spaces` defines observation leaf paths as
`('current', channel.dss_class, channel.object_name, channel.quantity)`. The original test
wrongly assumed the authoring label was a public Gym dictionary key.

The corrected test checks the canonical `current` root, then iterates the actual resolved A04
observation bindings, traverses each compiled path in both the controller snapshot and the
`env.reset()` observation, and verifies equality of all leaf values using NumPy's exact array
comparison. This strengthens the A05I6 nonmutating observation-copy check without modifying
the observation schema. The original failing qualification evidence remains preserved.

## Immutable boundaries

No changes to `src/` at all. A03/A04, physical actuals, replay, forecast, uncertainty,
R02A backend, controller implementation/science, and both repository IEEE-123 feeders are
unchanged. No new exogenous faults or additional Snapshot solves. A04 Gym schema unchanged.

## Independent acceptance

Verify **all** 241 predecessor source hashes, the predecessor install receipt, and the original
failed qualification evidence before replacement. Install exactly this one test replacement
plus this documentation file, yielding **242** manifest-controlled files. Require the targeted
suite followed by three fresh-process full regressions, no skipped tests, no JSON decode errors,
and source-preservation checks after every run. Native Windows R01 exception traces and the
mitigated-but-open R02 reliability concern remain separately reported and **open**.

The A05 V1 final freeze requires a separate explicit review after successful qualification.
