# B00I2R2: Preserve native boolean diagnostics in B00 serialization

## Scope and cause

The R1 repair was installed, but its four native IEEE-123 integration cases failed at
`REGCONTROL_ENABLED_NOT_READABLE`. The B00 runner's recursive `_plain()` serializer
converted Python `True` and `False` into integer 1 and 0 because it checked
`(np.integer, int)` before `bool` (which is an `int` subclass). The AltDSS
backend already emits regulator `enabled` values as genuine Python booleans.
The P0 metrics consumer deliberately enforces boolean semantics.

## Minimal authorized patch

1. `experiments/pesgm2027/b00_native_controls/run_b00.py`: preserve Python
   `bool` and `numpy.bool_` before generic integer conversion. No other
   behavior changes, including the B00I1 opt-in default.
2. `tests/unit/controllers/test_b00i2_metrics_renderer.py`: add two tests for
   both true/false and NumPy booleans, nested values, JSON round-trip,
   seven-regulator recorder acceptance and the existing offline renderer.
3. Add this documentary explanation.

No native solver, control queue, A03/A04/A05 contract, IEEE-123 feeder,
P2 configuration, or production controller algorithm is modified.

## Acceptance and limitations

Pin to exactly 263 B00I2R1 installed-but-unqualified files plus 56 separate
P2 assets; preflight must fail on drift or reinstall. Require the six R1 queue
tests, fifteen recorder/renderer tests (13 predecessor + 2 new), four native
integration cases, 12 B00I1 regressions, 99 A05 regressions, and three full
224-test regressions. The native 24-step four-feeder diagnostic campaign must
produce recorded metrics and HTML dashboards; never manufacture native events.
Accept engineering qualification only after independent evidence review. The
B00 science freeze remains separate. R01 remains OPEN and R02 remains
OPEN with qualified mitigation.
