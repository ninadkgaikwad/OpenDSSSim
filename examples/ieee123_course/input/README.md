# Course input data — provenance and scope

- `feeders/` copies the provided OpenDSSSim IEEE-123 baseline, P1 10-PV augmentation, and the original P2 MF01/MF02 scenario files **byte for byte**. Original feeder license and provenance files are retained. These are self-contained DSS input folders; `IEEE123Master.dss` has local `Redirect` references.
- `mpc_baseline/` is the pinned A07A2 offline AltDSS parameter capture (`CASE_PINS.json`, case JSON, static discovery JSON), included for reproducible MPC lessons. It is **not** a replacement for current measured operating state; the online controller reads its current observation and forecast through `ControllerContext`.
- `qualified_routes/` is the original S10D P2 selected-route evidence. P2 RBC continuation **does not** constitute a newly solved electrical evaluator at every step.
- `geometry/` includes IEEE-123 **diagram coordinates**, not latitude/longitude. Use for illustrative network plots only.
- `reference_results/` contains selected plot-ready datasets from the audited V06 paper-writer bundle, for teaching plotting without a solver. These are qualified archived research outputs; generated output remains in `output/<run-id>/`.

See `input/SHA256_INPUT_MANIFEST.csv` and `docs/release/INPUT_PROVENANCE.md` for the exact evidence and scientific limitations. Do not rewrite source cases or feeder physics to improve plots.
