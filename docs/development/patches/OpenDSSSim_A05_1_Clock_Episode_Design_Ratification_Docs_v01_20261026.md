# OpenDSSSim A05.1 - Clock and Episode Design-Ratification Documentation Patch

**Patch ID:** `OpenDSSSim_A05_1_Clock_Episode_Design_Ratification_Docs_v01_20261026`  
**Ratified:** 2026-10-26  
**Patch class:** Documentation-only; additive; no runtime implementation  
**Predecessor:** A04I4A v02, 195 source files, manifest SHA256 `5E2C6DE82802533C283EB884987B999345D9BAFBFD6C09A439949B8C15A47045`

## Scope

Add exactly one A05.1 design authority document under `docs/development/stages/A05_temporal_exogenous_integration/` and this patch record under `docs/development/patches/`. Do not overwrite or revise any frozen A01-A04 file, repository Python source, tests, fixtures, semantic registries, preflight records, or existing documentation.

The design authority is:

`docs/development/stages/A05_temporal_exogenous_integration/01_A05_1_Clock_Episode_Semantics_RATIFIED_20261026.md`

It captures the 2026-10-26 ratification of the external UTC clock, first-common-sample reset, Option A current-interval Snapshot solve, `ControlMode=STATIC`, optional read-only user callback view, defaults for reset/reward/termination/truncation, finite episode boundary, temporal audit, error lockout and the A05 cross-stage deferrals.

## Qualification boundaries

The installer must verify **every one** of the original 195 predecessor source files against the original qualified manifest before creating either Markdown file. The manifest itself must hash exactly to the frozen SHA256 above. New documentation is installed only at two never-before-present paths; preexisting files are preserved and cause a fail-closed refusal rather than overwrite. A separate validator checks both new files and all 195 predecessors, generates a successor 197-row source manifest and emits a PASS/FAIL evidence report to Windows Downloads.

The documentation package is distinct from the A05 executable/runtime implementation. Passing its validator establishes only **documentation patch qualification**, not A05 clock, native-control, exogenous-input or benchmark behavioral qualification.

## Rollback

A separate guarded rollback utility may move only the two newly installed files, and only when they match the exact packaged bytes, into a timestamped recovery directory under Downloads. All 195 original A04I4A source files remain untouched. Changed documents are not removed automatically.

## Next stage

Proceed to **A05.2 - External Load, PV, and Weather Input Contracts**, beginning with dataset-to-device identity, physical units and per-device versus shared-signal mapping. A05.2 design discussions do not authorize any source implementation.
