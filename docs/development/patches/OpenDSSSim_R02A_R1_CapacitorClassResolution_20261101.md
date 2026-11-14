# R02A-R1: Native capacitor class-name normalization (qualification repair)

## Predecessor and incident

The R02A V01 backend patch was installed onto the A05I2 219-file state and produced
an unqualified 222-file successor. Independent R02A targeted validation returned
**41 passed, 2 failed**, both in the newly added IEEE-123 capacitor readback cases.
Full regression was not started. No `JSONDecodeError` was observed in that targeted
run; the separate R01 native exception traces persisted.

The integration test's discovery map deliberately case-folded object names,
producing `capacitor.c83`. `_resolve_native_object` performed
`getattr(self._context, 'capacitor')`, but the native AltDSS manager is `Capacitor`.
The subsequent exact `FullName` check already compared names case-insensitively.

## Minimal change

One backend-source edit maps only class names with `casefold() == 'capacitor'`
to AltDSS's published `Capacitor` manager. Other class lookups remain unchanged;
object name is never broadened, and the existing `FullName` identity gate
continues to reject wrong objects. There are no A03/A04/Plant/Problem/A05I2,
feeder, environment, or dependency modifications.

## Acceptance

The 222-file **installed but unqualified** R02A manifest is the exact predecessor.
Installation replaces only `src/opendsssim/backends/altdss_backend.py` and adds
this note and a unit regression suite. The new suite verifies capitalization
normalization, exact object identity, unknown-object failure and unchanged
non-capacitor behavior. Qualification requires all R02A/A05 targeted cases
including both native IEEE-123 feeders, then three fresh-process full
regressions with zero JSON decode failures, plus before/after source checks.

R01 and R02 remain OPEN until independent evidence review. A05I2 and A05I3
are not automatically qualified by installing this repair.
