# OpenDSSSim A05.3 Time-Series and Replay - Documentation-Only Patch v01

**Date:** 2026-10-26 (America/Los_Angeles)  
**Authority:** User ratification of A05.3.1-A05.3.7 with changes to timestep and replay defaults  
**Status:** DESIGN RATIFIED; ADDITIVE MARKDOWN ONLY; RUNTIME NOT IMPLEMENTED

## Predecessor and scope freeze

- Qualified predecessor: A05.2 documentation-only successor, 199 files.
- Exact predecessor source-manifest SHA256: A09F067119FD12D0DDB9F07E0E703BB8874102DAC95AFC0042964B8BA40DDD36.
- Guarded installer verifies the original 199-file source-manifest file on the authoritative laptop and checks all pinned source files before adding two new docs, never overwriting installed files.
- New successor after laptop qualification: 201 pinned source files. No Python source, environment, feeder assets, benchmarks or science runs change.

## Ratified A05.3 decisions

1. CSV and Parquet sources; explicit timestamp, columns, units, source hashing; common typed internal representation and a safe custom-reader boundary.
2. One episode dt, infer only a unique common timestamped-source cadence, require explicit dt for mixed cadences. If **no timestamped exogenous source** and no user dt: generic default **3600 seconds** (one hour).
3. UTC conversion, first jointly valid required-source timestamp by default, explicit qualified alternatives and deterministic DST/missing/duplicate handling.
4. Source replay modes strict and tile; **default tile**. Tile wraps data indices without rewinding logical time, plant or native controllers.
5. Exact sample default, optional declared linear interpolation or zero-order hold, gap validation and no implicit energy/power conversion.
6. Positive integer episode horizon N independent of source duration. In normal completed N-step episodes: one reset solve plus N step solves, and reset/step0 share d[0].
7. Per-source original timestamp/index, logical time, wrap/provenance and history retained with failure lockout; no future-truth disclosure by accident.

## Explicit non-goals

- Do not alter A03, A04, A05.1 or A05.2 implementations or previously ratified Markdown.
- Do not create OpenDSS Daily/Yearly/Duty native runs, new physical/action semantics, a fabricated default profile, or unqualified interpolation/extrapolation.
- Do not qualify A05 runtime here. Genuine AltDSS tests and implementation staging remain separately required.

## New documents

1. docs/development/stages/A05_temporal_exogenous_integration/03_A05_3_Time_Series_Indexing_and_Replay_RATIFIED_20261026.md (authoritative ratified design).
2. docs/development/patches/OpenDSSSim_A05_3_Time_Series_Replay_Design_Ratification_Docs_v01_20261026.md (this patch lineage).

## Next

A05.4 forecast source, issue-time, horizon and information contract follows after documentation qualification.
