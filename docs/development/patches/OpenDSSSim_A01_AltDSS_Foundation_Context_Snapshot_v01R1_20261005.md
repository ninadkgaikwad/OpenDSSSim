# OpenDSSSim_A01_AltDSS_Foundation_Context_Snapshot_v01R1_20261005

## 1. Patch ID / Date
- Patch ID: `OpenDSSSim_A01_AltDSS_Foundation_Context_Snapshot_v01R1_20261005`
- Date: 2026-10-05
- Stage: A01

## 2. Objective
Establish the smallest executable OpenDSSSim vertical slice:

`DSS master -> independent AltDSS context -> snapshot solve -> typed SolutionResult -> minimal Gymnasium reset/step boundary`.

## 2A. v01 -> v01R1 Correction History
The original v01 installer attempt on 2026-10-05 reached Python compile and then failed the standalone validator during package import. The failure was a circular import introduced by the eager package export in `src/opendsssim/plant/__init__.py`:

`backends.base -> plant.solution -> plant.__init__ -> plant.core -> backends.base`.

The v01 installer automatically rolled back every newly created payload file and reverified the four PRE-A01 predecessor files byte-for-byte. Therefore v01R1 retains the same PRE-A01 predecessor identity.

v01R1 changes only the packaging/import boundary plus a regression test:
- `plant.__init__` imports `SolutionResult` eagerly but exposes `OpenDSSPlant` lazily through module `__getattr__`;
- `tests/unit/test_import_graph.py` proves top-level package, backend-base, plant-solution, and lazy plant imports coexist without circular initialization.

No A01 physics, AltDSS semantics, Gymnasium semantics, persistence schema, or scientific scope changed.

## 3. Predecessor
Authoritative PRE-A01 repository source-manifest artifact SHA256:

`175411EEB2EFB0697D929E69DBD6EDCFE5524595A1E5D6F5426780EA9631E161`

A0 architecture plan SHA256:

`BE73154DEF4C1E2BB3BE149844BF7C322A85346D40B009B9F5C5CD3588D7FF49`

SmartCommunitySim2 architecture-audit SHA256:

`92C117CB7FB8F316146E3DFFA56F6BC151822E110DCEB30C3DF0A30CE9BB3B47`

## 4. Input Bundles
- `OpenDSSSim_A01_DirectedInput_v01_20261001_171733.zip`
- Bundle SHA256: `01EE0943E529C01B5B69E4D6E3504C35B247A05C4F6B526CC522D4499B4EBC34`
- Environment: `scalebridge-dev-gpu-laptop`
- AltDSS prerequisite: `altdss==0.2.4`

## 5. Architecture / Science Decisions
- One `OpenDSSSimulator` instance owns one independent AltDSS context.
- `reset()` clears/reloads the circuit inside the same owned context.
- OpenDSSSim, not AltDSS intrinsic time-series modes, will own future episode time.
- A01 uses one authoritative snapshot solve per `step({})`.
- Controller science is absent.
- A01 uses an empty Gymnasium `Dict` action space only as lifecycle scaffolding.
- No generalized state/action discovery is introduced.
- The fixture is software qualification only and is not the PESGM scientific benchmark.

## 6. Files Changed
This patch adds:
- `pyproject.toml`
- `src/opendsssim/**` A01 package foundation
- `tests/fixtures/a01_minimal/Master.dss`
- A01 unit/integration tests
- `scripts/validation/validate_a01.py`
- this patch record

No PRE-A01 file is modified.

## 7. Non-Goals
Not implemented:
- capability discovery;
- circuit/state/action/disturbance/constraint/parameter registries;
- external load/PV/weather profiles;
- strict/tile/noise;
- `ProblemSpec`;
- external controllers;
- requested/applied/realized action semantics;
- native/external control authority;
- H0-H3 history;
- FAST/STANDARD/AUDIT;
- IEEE-123;
- MPC;
- RL;
- Gurobi;
- visualization;
- BuildingsToGridSim coupling.

## 8. API Changes
New public foundation:
- `opendsssim.OpenDSSSimulator`
- `opendsssim.SolutionResult`
- `opendsssim.backends.AltDSSBackend`
- `opendsssim.network.CircuitSource`

A01 Gym semantics:
- `reset()` recompiles/restores the same circuit in the same AltDSS context and solves one snapshot.
- `step({})` solves one snapshot.
- any non-empty action is rejected in A01.

## 9. Config / Schema Changes
- package version: `0.1.0a1`
- required runtime dependency: `altdss==0.2.4`
- runtime provenance schema added under `persistence/schema.py`

## 10. Tests / Validators
Targeted tests cover:
- DSS source validation/hash;
- typed result serialization;
- backend circuit-load/solve/close;
- Gym reset/step action contract;
- source identity and atomic runtime manifest;
- two-environment context isolation;
- snapshot convergence;
- deterministic reset in same context.

Standalone validator:
`scripts/validation/validate_a01.py`

## 11. Installer Command
From authoritative OpenDSSSim repo root:

```powershell
& "$HOME\Downloads\Install-OpenDSSSim_A01_AltDSS_Foundation_Context_Snapshot_v01R1_20261005.ps1" `
    -RepoRoot (Get-Location).Path `
    -PatchZip "$HOME\Downloads\OpenDSSSim_A01_AltDSS_Foundation_Context_Snapshot_v01R1_20261005.zip"
```

## 12. Validation Command
From authoritative OpenDSSSim repo root:

```powershell
& "$HOME\Downloads\Validate-OpenDSSSim_A01_AltDSS_Foundation_Context_Snapshot_v01R1_20261005.ps1" `
    -RepoRoot (Get-Location).Path `
    -OutputDir "$HOME\Downloads"
```

## 13. Pass Markers
Expected:
- `A01 INSTALLER: PASS`
- `A01 STANDALONE VALIDATOR: PASS`
- `A01 PYTEST: PASS`
- `A01 QUALIFICATION: PASS`

## 14. Rollback
The installer records files created by this patch. If install-time validation fails, newly created files are removed automatically while predecessor files are preserved.

Manual rollback before successor patches:
remove only files listed by the patch payload manifest, then prune empty directories. Do not modify the four PRE-A01 predecessor files.

## 15. Known Limitations
- A01 does not expose generalized feeder state.
- A01 supports only the AltDSS backend.
- A01 has an empty external action surface.
- A01 does not own episode/time-series progression yet.
- `process_time_s` is diagnostic and not a deterministic replay quantity.
- Runtime source identity is a pre-Git repository digest, not a Git commit.

## 16. Next-Stage Entry Criteria
A02 may begin only after laptop qualification proves:
- independent contexts;
- snapshot convergence;
- deterministic reset/recompile;
- package import;
- Gym lifecycle;
- runtime provenance;
- predecessor byte preservation.

## 17. Planned Successor
A02: engine + circuit capability discovery and native OpenDSS object/capability introspection.
