# Patch Record - OpenDSSSim_A04_6_ControllerTransformationBoundary_Design_Ratification_Docs_v01_20261017

**Date:** 2026-10-17
**Type:** Additive A04.6 design-ratification documentation patch
**Runtime/source implementation:** None
**Environment mutation:** None

## Predecessor Authority

- Qualified repository files: 147
- Qualified source-manifest SHA256: `93F50E0BA994DE4DB5AF8DE7AB7CB8E78CD15976B5C61E8EBE2045A509BF84F2`
- A04.1 through A04.5: RATIFIED + DOCUMENTED + QUALIFIED

## Added Files

1. `docs/development/stages/A04_problem_spec_gym_dict/06_A04_6_ControllerTransformationBoundary_RATIFIED_20261017.md`
2. `docs/development/patches/OpenDSSSim_A04_6_ControllerTransformationBoundary_Design_Ratification_Docs_v01_20261017.md`

## Ratified Scope

A04.6 freezes a deliberately minimal controller-transformation boundary:

- no derived-observation engine in OpenDSSSim v1;
- no generic observation/action wrapper framework in OpenDSSSim v1;
- controller preprocessing belongs to RBC/MPC/RL implementations;
- base plant remains canonical semantic Dict observation/action;
- all controller actions still enter through `env.step()` and therefore A04.4/A04.5.

Reward/termination/truncation remain plant responsibilities:
- plant owns abstract invocation hooks;
- defaults exist internally;
- ProblemSpec may supply custom callables;
- exact signatures and runtime binding are deferred to A04.7.

## Status After Patch

- A04.1 - done
- A04.2 - done
- A04.3 - done
- A04.4 - done
- A04.5 - done
- A04.6 - RATIFIED + documented
- A04.7 - next

## Scope Guard

Design documentation only. Runtime implementation remains unauthorized until the complete A04 design is frozen.
