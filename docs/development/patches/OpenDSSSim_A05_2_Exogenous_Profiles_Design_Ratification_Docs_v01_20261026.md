# OpenDSSSim A05.2 Exogenous Profiles - Documentation Patch v01

**Date:** 2026-10-26  
**Authority:** user ratification of A05.2.1-A05.2.7, including Faiman-style PV temperature with constant 25 degC when weather inputs are unavailable  
**Status:** DOCUMENTATION-ONLY ADDITIVE PATCH; DESIGN RATIFIED; CODE NOT IMPLEMENTED

## Predecessor freeze

- Qualified predecessor: A05.1 documentation successor, 197 files, source-manifest SHA256 `41E68C88F850130CD6D556AF2B36BF3DB54E5B266216E3E3D4BFA478E6DE837C`.
- This installer validates the exact 197-file manifest produced on the user's authoritative laptop. It does not modify the A04I4A native runtime, A03 semantic compiler, or A05.1 documentation.
- Expected additive payload: exactly two new Markdown files, yielding a qualified 199-entry successor only after laptop-side independent qualification.

## Added documents

1. `docs/development/stages/A05_temporal_exogenous_integration/02_A05_2_External_Profiles_Physical_Mapping_RATIFIED_20261026.md`: authoritative A05.2.1-A05.2.7 contract; source-to-native mapping, three load modes, PV irradiance/temperature, Faiman, 25 degC fallback, strict semantic authority and qualification boundaries.
2. `docs/development/patches/OpenDSSSim_A05_2_Exogenous_Profiles_Design_Ratification_Docs_v01_20261026.md`: patch lineage, scope and qualification notes (this file).

## Source-grounded A03 compatibility decision

A03 currently labels `Load.kW`/`Load.kvar` as step-exogenous, PV availability via `Irradiance` or fallback `pctPmpp` as step-exogenous, and PV `kvar` as controllable. A03 does **not** include a step-exogenous `PVSystem.Temperature` entry. A05 will add a versioned and fail-closed exogenous-binding extension to qualified native array-temperature endpoints **without altering frozen A03**. The extension is a future implementation gate, not functional code delivered here.

## Weather refinement and explicit default

With mapped, valid ambient-air temperature, wind speed and PV plane-of-array irradiance, use

`T_array = T_outside + G_POA/(U0 + U1*v_wind)`.

`G_POA` uses W/m^2 in this equation; native irradiance in kW/m^2 is multiplied by 1000. Defaults in Faiman mode are `U0=25.0`, `U1=6.84` unless explicitly overridden with qualified coefficients, and their provenance must be retained. Where a complete ambient/wind binding is **not provided**, use a recorded constant `T_array=25 degC`. A missing sample **inside a declared Faiman input** is an error, not a reason to change model mid-episode. Input cleaning, timestamp normalization and replay remain A05.3 work.

## Qualification and implementation status

- Patch installation verifies the qualified 197-entry predecessor, two payload hashes, and refusal to overwrite existing targets.
- Post-install validator generates a 199-entry qualified source manifest and JSON PASS receipt in Downloads.
- Neither packaging nor laptop docs qualification establishes correctness of OpenDSS/AltDSS temperature writes, load-setter order, profile playback, or any A05 runtime functionality.
- A05.3 follows this design. Implementation proceeds only when the complete stage implementation gates are separately approved.

## Reference pointers

- A05.1 ratified document: `docs/development/stages/A05_temporal_exogenous_integration/01_A05_1_Clock_Episode_Semantics_RATIFIED_20261026.md`.
- A03 semantic compiler: `src/opendsssim/semantics/compiler.py`.
- Device physics: https://dss-extensions.org/dss-format/Load.html and https://dss-extensions.org/dss-format/PVSystem.html.
- Faiman temperature model: https://pvpmc.sandia.gov/modeling-guide/2-dc-module-iv/module-temperature/faiman-module-temperature-model/.
