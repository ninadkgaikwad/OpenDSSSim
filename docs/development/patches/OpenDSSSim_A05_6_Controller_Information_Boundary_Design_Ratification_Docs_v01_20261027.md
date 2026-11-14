# OpenDSSSim A05.6 — Documentation-Only Design Ratification Patch

**Date:** 2026-10-27 (America/Los_Angeles)  
**Status:** A05.6 DESIGN RATIFIED — no runtime source implementation or verification claimed.

## 1. Immutable predecessor and two-file additive patch

The user reported `PASS_A05_5_DOCUMENTATION_ONLY` for **205** predecessor source files, with qualified manifest `OpenDSSSim_A05_5_DocsOnly_Qualified_SourceManifest_20261028T003509205Z.csv` and SHA256 `50EA36EA13A4E07BBF7B78B88AD71453DE60A51551D8C0F4E1D52EA9A6D2DB7E`. The actual CSV is not contained in this package; the installer requires it from the user's Downloads folder and checks its exact byte hash and **every predecessor source file's size and SHA** before any write. Thus the user-reported qualification is treated as a guard, not as an independently observed current-repository fact.

This patch adds **exactly two Markdown files**:

1. `docs/development/stages/A05_temporal_exogenous_integration/06_A05_6_Controller_Information_Boundary_RATIFIED_20261027.md` — full ratified 6.1–6.8 contract.
2. `docs/development/patches/OpenDSSSim_A05_6_Controller_Information_Boundary_Design_Ratification_Docs_v01_20261027.md` — this patch provenance and acceptance contract.

After installation the qualified manifest must contain **207** distinct predecessor-plus-new paths, with 205 original byte-identical files and only the two additions. The installed validator writes a new source-manifest CSV and JSON receipt into Downloads. No source files, feeder circuits, data, virtual environments, installed dependencies or existing docs are modified or overwritten.

## 2. Ratified user refinements to A05.6

| Clause | Ratified result | User refinement captured |
|---|---|---|
| 6.1 | Distinguish hidden plant truth, authorized measurement, authorized forecast and trusted diagnostics | Present device health, enabledness and availability belong in authorized controller information where available; unknown status is explicit. |
| 6.2 | Keep Option-A decision clock distinct from electrical sample timestamp | Agreed without change. |
| 6.3 | Respect A04 ProblemSpec-resolved nested Gym observation and its fields | Preserve existing recording H0–H3 and FAST/STANDARD/AUDIT, richer recording must not change physics. |
| 6.4 | Controller forecasts only from A05.4/A05.5 approved exogenous-derived service | Forecasts may also be declared as Gym observation fields, with qualified shape/visibility; no undeclared auto-add. |
| 6.5 | Provide read-only permitted controller context and static/current grid/device metadata | Agreed; source-bus inference, MPC/RL transformations and curtailment strategy remain controller-side. |
| 6.6 | Equal permitted P1 or P2 information and action entitlements for RBC/MPC/RL | Controller decides whether and which forecasts/horizon it needs, subject to service permission and availability; report actual information consumption. |
| 6.7 | Protect official observation, info and context boundaries | Proportionate responsibility: the simulator guarantees its official interface; controller owns its information requests/usage; no universal sandbox for arbitrary external code. |
| 6.8 | Negative tests, physical invariance, time alignment, provenance and regressions | Agreed with all above amendments. |

## 3. Preserved authorities

- Plant != Problem != Controller. Plant truth/exogenous/event application and AltDSS solve remain separate from ProblemSpec observation projection and controller feature/action logic.
- A03 registered capabilities, circuits, states, controls, disturbances, constraints and parameters; A04 strict Gym spaces, authority and visibility remain in force. Do not retroactively edit frozen predecessors to make the new A05 docs appear implemented.
- A05.1 Option-A step timing; A05.2 typed external load/PV/weather mappings; A05.3 strict/tile replay and default dt; A05.4 one-source forecast service; A05.5 `none` or additive Gaussian single-seed, single-trajectory forecast-only error.
- One existing AltDSS context per environment; snapshot solves are the physical authority. Forecast, context and observation reads must not perform electrical solves.
- IEEE-123 baseline native regulator/capacitor equipment remains unchanged; only ratified 10 PV additions for the shared P1 feeder, without hard-coded cardinality in generic A05 components.

## 4. Evidence and gates

The package must fail before writing if the predecessor manifest path is missing, hash/count/entry invalid, a predecessor file drifts, a target already exists, or the payload differs from pinned SHA256. The validator independently rechecks all 207 files and emits the successor manifest and a qualifying JSON receipt with `runtime_implementation_qualified=false`.

Qualification is **documentation-only**, not a passing runtime acceptance test. A05.7 remains for ratification. After A05.7 documentation freeze, develop gated A05 implementation and run real AltDSS, Gym/SB3 and whole-repo regressions before any scientific P1/P2 controller campaign. No scientific control results are claimed here.
