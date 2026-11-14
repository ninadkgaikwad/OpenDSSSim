# Patch Record - OpenDSSSim_A04_4_Gymnasium_DictSpace_Compilation_Design_Ratification_Docs_v01_20261014

**Date:** 2026-10-14
**Type:** Additive A04.4 design-ratification documentation patch
**Runtime/source implementation:** None
**Environment mutation:** None

## Purpose

Persist the ratified A04.4 Gymnasium Dict-Space Compilation contract.

## Predecessor Authority

- Qualified repository files: 143
- Qualified source-manifest SHA256: `A29E395FE85684E8FAE9F8DB7431DDF9A1DFBF9604FE283BDE21A89C01A587A7`
- A04.1: RATIFIED + DOCUMENTED + QUALIFIED
- A04.2: RATIFIED + DOCUMENTED + QUALIFIED
- A04.3: RATIFIED + DOCUMENTED + QUALIFIED

## Added Files

1. `docs/development/stages/A04_problem_spec_gym_dict/04_A04_4_Gymnasium_DictSpace_Compilation_RATIFIED_20261014.md`
2. `docs/development/patches/OpenDSSSim_A04_4_Gymnasium_DictSpace_Compilation_Design_Ratification_Docs_v01_20261014.md`

## Modified Files

None.

## A04.5 Mandatory Carry-Forward

A04.5 must explicitly ratify generalized fault association in `ProblemSpec`:
- any OpenDSS device/element may be fault-associated;
- the faulted device is forced `Enabled=False`;
- the device remains semantically present;
- normally selected action channels remain structurally present in the static space;
- associated requested controls are inadmissible while disabled;
- normal controller actions cannot re-enable/re-energize the faulted device;
- exact fault provenance, reset/runtime application, rejection status, authority interaction, and admissibility enforcement are A04.5 scope.

## Status After Patch

- A04.1 - done
- A04.2 - done
- A04.3 - done
- A04.4 - RATIFIED + documented
- A04.5 - next
- A04.6 - pending
- A04.7 - pending

## Scope Guard

Design documentation only. No runtime implementation is authorized.
