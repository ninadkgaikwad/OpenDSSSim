# Patch Record - OpenDSSSim_A04_5_Constraints_ControlAuthority_Design_Ratification_Docs_v01_20261015

**Date:** 2026-10-15  
**Type:** Additive A04.5 design-ratification documentation patch  
**Runtime/source implementation:** None  
**Environment mutation:** None

## Predecessor Authority

- Qualified repository files: 145
- Qualified source-manifest SHA256: `C74163531B1F95F0F15A69D07319B61EB3A1344F6403390ACE0386B0053FBDD4`
- A04.1 through A04.4: RATIFIED + DOCUMENTED + QUALIFIED

## Added Files

1. `docs/development/stages/A04_problem_spec_gym_dict/05_A04_5_Constraints_ControlAuthority_RATIFIED_20261015.md`
2. `docs/development/patches/OpenDSSSim_A04_5_Constraints_ControlAuthority_Design_Ratification_Docs_v01_20261015.md`

## Key Ratified Simplification

A04.5 does not duplicate OpenDSS electrical-feasibility logic. After A04.4 Gym validity it enforces only finite numeric sanity, fault/device availability, and NATIVE/EXTERNAL/HYBRID actuator ownership. AltDSS/OpenDSS remains authoritative for native electrical/network/device behavior.

## Fault Contract

ProblemSpec may fault any qualified OpenDSS device/element. The target remains semantically present, is forced `Enabled=False`, and its normal action channels remain structurally present but are not applied while fault-disabled. Normal controller actions cannot clear the fault or re-enable the target.

## Native-Control Contract

ProblemSpec/reset configures native-control ownership once for the episode. Ordinary runtime actions cannot turn native controls on/off, retune them, or change ownership.

## Status After Patch

- A04.1 - done
- A04.2 - done
- A04.3 - done
- A04.4 - done
- A04.5 - RATIFIED + documented
- A04.6 - next
- A04.7 - pending

## Scope Guard

Design documentation only. Runtime implementation remains unauthorized.
