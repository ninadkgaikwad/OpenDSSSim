# R02A: targeted AltDSS capacitor discovery serializer reliability amendment

**Stage:** independently qualified reliability repair to frozen A02 backend, authorized after A05I2 installed but failed full regression.

## Evidence and scope

The A05I2 physical mapping targeted suite passed, while full regressions intermittently failed at `json.loads(obj.to_json(_DISCOVERY_JSON_FLAGS))` for `Capacitor.cap1` within `_discover_objects`. Six fresh-process diagnostic runs reproduced the intermittent failure. The 16-context native forensic probe produced syntactically valid JSON but varied the *unconfigured* `CMatrix` property in every full-serialization sample; its sparse explicit-property export was stable. `CMatrix` was not set in `tests/fixtures/a03_semantic/Master.dss` (the capacitor was configured using `kvar`). The direct evidence does **not** prove whether the matrix buffer alone causes malformed JSON, and must not be generalized to all classes.

## Narrow implementation decision

- Change exactly `src/opendsssim/backends/altdss_backend.py` for class `Capacitor` only.
- Instead of requesting `DSSJSONFlags.Full` for capacitor objects, request explicit native JSON (class/name included) and supplement existing A02/A03 baseline properties via the documented typed native getters, including phase, P/Q ratings, states, connection, enabledness, bus names and relevant defaults.
- Do not retrieve or serialize **unconfigured** `CMatrix`; retain and validate *explicitly configured* `CMatrix` from sparse JSON, fail closed on malformed explicit data, missing getter, or non-finite fields.
- Keep other native object classes, `_DISCOVERY_JSON_FLAGS`, frozen A03 policy and compiler, A04 authority, A05I2 source, and both IEEE123 feeder files unchanged.
- Preserve the distinction between native physical properties and observation/control authority. This is serialization/readback only, never an AC solve, circuit mutation, or fault policy change.

**Semantic difference:** the unconfigured `CMatrix` property, whose Full export was unstable, is intentionally absent from capacitor discovery. For other capacitor fields the implementation derives current typed engine values. This is a narrowly approved exception to A02 Full-property enumeration; report it explicitly rather than asserting byte-identical pre/post A02 snapshots.

## Qualification gates

1. Full installed 219-file A05I2 predecessor verified against `OpenDSSSim_A05I2_Installed_SourceManifest_20261101T184243932526Z.csv`, SHA256 `37440E8B824921EEDBAEABDA82086C0AC94AEE6CB1C57313A243A61452697BDF`.
2. Validate exactly one backend source replacement and three additions (two tests and this note); no user worktree overwrites.
3. Unit tests: stable typed default acquisition, explicit matrix retained, bad explicit JSON rejected, native readback missing-property rejection and other classes retain Full export.
4. Genuine AltDSS tests: 12 independent A03 fixture contexts; both canonical and P1 working IEEE123 feeder capacitor discovery and native readback.
5. Independent A05I1/A05I2 targeted suite and three full fresh-process repository regression suites, all exit zero with no R02 JSON failures.
6. Inspect test stdout/stderr for `Windows fatal exception: code 0xe0465043`, which remains unresolved **R01** even if suites pass. Do not claim that R01 or all native issues are resolved.
7. Record source hashes, runner version, test outcomes, predecessor/successor manifests, snapshots and provenance in Downloads. Failure leaves installed state pending inspection; no silent reinstallation.

A05I3 remains unauthorized until the combined A05I2 + R02A state meets independent acceptance and the user ratifies the qualification evidence.
