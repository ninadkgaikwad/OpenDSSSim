# A04I4 — Full Behavioral Qualification and Implementation Freeze (candidate v01)

## Contract

Validation-only, additive successor to A04I3 v01R3: all 188 predecessor source files MUST match the qualified manifest, SHA256 `9261E8F5D83DD3D376D05F62303C80E449B8478206035E6942EC0CC7B46FC268`. Exactly three additive files, no changed/removed files. All 188 original files frozen (including package version `0.1.0a6`). No dependency, environment, circuit, registry, semantic, or run-configuration mutation.

## Qualification

1. Verify exact qualified predecessor bytes and no unrelated extra files.
2. Compile Python and run added genuine AltDSS behavioral tests: multi-step repeated commands, observations, per-step realized audit, contextual identity, H3 history, reset, EXTERNAL and HYBRID authority, two-run preflight reuse/lineage, and SWITCHES fail-closed without SwtControl mutation.
3. Run the complete repository pytest suite including the inherited A01–A04I3 tests.
4. Independently run A03, A04I2, A04I3 standalone validators; A04I2 `package_version` discrepancy is only a documented successor-version exception, never rewritten as PASS. All other gates MUST PASS.
5. Produce and independently hash a final 191-file source manifest and evidence report. Only this genuine validation on the authoritative Windows AltDSS environment qualifies the freeze.

## Non-goals and scientific caveats

A05 time, exogenous load/weather/PV profiles, forecast synchronization, temporal fault schedules, controller design and P1/P2 experiments are excluded. `SWITCHES` relationship is deliberately NOT considered `CONTROLS`: external switching involving native SwtControl is unsupported until an explicit future contract revision. Thus A04I4 freeze certifies the implemented subset; it does not certify complete P2 switching functionality. A04I4 is not qualified solely by code compilation or local static checks.
