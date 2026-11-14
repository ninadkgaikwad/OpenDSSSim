# B00I2 consolidated P0 + P1 + P2 science-instrumentation contract

## Scope and authority

One additive, read-only instrumentation patch, grounded in the B00I1 253-file qualified source, the 56 separately tracked P2 assets, the newly collected repository tree, and directed source ZIP. B00I1 remains the unchanged-default path. The B00I2 runner uses the same solver context and only empty external actions; no extra solve, no switch restoration, no feeder mutation, no independent AltDSS context. The opt-in diagnostic accessor is **not** part of the controller-information boundary and is not controller-readable through `controller_context()`.

The patch explicitly modifies two pre-existing runtime source files (`backends/altdss_backend.py`, `environment/simulator.py`) to authorize detached diagnostic readbacks. This must be treated as a separately qualified extension, not a declaration that all frozen A03/A04/A05 bytes stayed unchanged. The A05 Gym observation/action spaces and native electrical dynamics must remain behaviorally identical. The third modified pre-existing file is the B00 experiment runner; it defaults to its previous B00I1 behavior.

## P0: native settings, regulator enablement, losses

After each authoritative native solve, collect engine readback of actual `Solution.ControlMode`, snapshot `Mode_str`, `MaxControlIterations`, `ControlIterations`, `ControlActionsDone`, clock settings, enabled flags and selected typed settings for the seven `RegControl` objects, and complex `AltDSS.Losses()` converted W/var to kW/kvar. A recognized STATIC mode is required for this specific baseline, not silently assumed. Missing enabled states, missing regulators, or nonfinite losses are failures. No native property writes or event pop operations are authorized.

## P1: episode electrical metrics and tap/cap state

B00I2 uses a 24-interval default (configurable 3–576 intervals) at a declared 3600-s step, deterministic synthetic load and PV profiles, all four primary IEEE123 feeders. Accumulate loss kWh from the executed step snapshots (not reset). Record energized voltage extrema, out-of-band phases, zero-voltage phases, per-step feeder P/Q, tap and capacitor state snapshots, and net **tap position difference proxies**, not mechanical tap operation counts. `None` is retained when trustworthy state readback is unavailable. P2 faulted feeders remain in PRE topology and no restoration is applied.

## P2: limited queue and native log diagnostics

Read the post-solve native control queue size and CSV representation, and the solution event log. Control queue inspection never calls `PopAction`, `DoAllQueue`, `SetAction`, `Push`, `ClearQueue`, or any mutator. Recorded logs are distinguished as initial, cumulative delta, restarted log, or unavailable. Under STATIC mode the queue can drain completely within each snapshot; **post-solve queue readbacks and event logs cannot prove physical action delays or complete intermediate event replay**. Full chronological event instrumentation remains a separately authorized future capability if rigorous dynamic delay validation is needed.

## Renderers

Offline HTML SVG charts are generated only from `result.json` and `b00i2_metrics.json`; no additional electrical computation is performed during rendering. A native four-feeder dashboard index and individual feeder dashboards show voltage, losses, control iterations, net tap proxy, queue pending count and tabular samples. Missing data are labeled unavailable, not converted to zeros.

## Acceptance and reliability

Consolidated acceptance runs 10 pure instrumentation/renderer unit tests, four feeder-native integration tests, the original B00 12-case tests, the A05 99-case regression, three fresh full-suite regressions (expected 213 tests each), and a real 24-interval / four-feeder campaign with recorder-backed HTML. Fail closed on nonzero exits, unexpected collection counts, skips, JSON decode errors and source drift. Preserve all evidence even on failure. R01 remains OPEN and R02 remains OPEN with mitigation qualified. B00 final science freeze is not automatic from a passing engineering installation.
