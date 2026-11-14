# A05I6R2: native switch-identity assertion repair (test-only)

## Evidentiary basis

- Baseline: installed/unqualified A05I6R1, 242 qualified-manifest files, SHA-256 `2E75046CA98665AED9114B750964671514A5AF76544DEAAB5EEB3C3148521D8E`.
- Failed targeted suite: 95 passed, four failed. Every failure occurs at an exact-case assertion `e.native_entity == "Line.Sw7"` in `test_a05i6_ieee123_controller_boundary.py`.
- Both qualified IEEE-123 master files define `New Line.Sw7`, and A05I6 controller-context assembly projects `inventory.elements` without removing or renaming native elements. AltDSS native element-name spelling is not a stable case-sensitive identity contract.

## Authorized change

Replace only the failing assertion with full inventory-to-context static-element parity and a case-insensitive `line.sw7` identity assertion. Preserve the requirement that the switch is present **exactly once**, is a three-phase line, and has two terminal bus specifications. If native discovery omits Sw7, the test still fails and will show a diagnostic cause.

The runtime backend, inventory, controller snapshot, physical replay, forecast uncertainty, Gym schema, and all feeder sources are unchanged. This amendment does not solve or close native reliability concerns R01 or R02, and does not qualify installed RBC/MPC/RL controller implementations.

## Acceptance

- Verify all 242 predecessor file hashes and original failed evidence and receipt.
- Install one integration-test replacement and this documentation file; expected successor count 243.
- 99/99 targeted A05/R02A tests, then three independent full repository regressions with 187/187 tests each; zero skips, zero JSON decoding errors, and no source drift.
- Record native exception traces separately. Rollback is guarded and only upon separate authorization.
