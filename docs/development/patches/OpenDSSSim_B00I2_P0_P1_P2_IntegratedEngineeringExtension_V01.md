# OpenDSSSim B00I2 P0/P1/P2 unified patch

This is a single guarded installation and validation campaign for three independently reported telemetry stages. Baseline: B00I1 (253 qualified files, exact manifest). All 56 P2 experimental assets have separate inventory provenance. Exactly three existing files are replaced, seven new files are introduced; original copies and predecessor manifest are backed up outside the repository. No feeder/master/DSS assets are changed. The A05 V1 Gym contracts remain intact; the new opt-in `native_diagnostics()` method and backend readback require full regression qualification.

The compact HTML renderer is offline and based solely on recorded data. Engineering acceptance is intentionally distinct from science freeze. The native control queue readback and event log are **not** complete timestamped event traces, and STATIC control mode is not a time-domain regulator-delay simulation.

Run only the bundled installer from the repo root. Do not reinstall after partial failure. Archive its evidence and investigate the failing gate. No automatic rollback after a failed native test; a separate guarded restore must be approved.
