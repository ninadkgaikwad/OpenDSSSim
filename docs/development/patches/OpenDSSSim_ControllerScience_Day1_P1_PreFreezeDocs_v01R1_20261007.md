# OpenDSSSim_ControllerScience_Day1_P1_PreFreezeDocs_v01R1_20261007

**Status:** Day-1 P1 documentation / pre-freeze  
**Date:** 2026-10-07

## Purpose

Close Day 1 of the generalized-controller science track by converting the three audited P1
sources and ratified design decisions into repository-owned documentation.

## Scientific status

This patch does **not** freeze P1 science for implementation.

It establishes the Day-1 pre-freeze contract:
- common simplified P1 physical problem;
- 10 regulator/tap + 10 capacitor + 10 PV-Q channels;
- common action/cost semantics;
- rule-based heuristic architecture;
- Gurobi-oriented LinDistFlow MIQP-MPC architecture;
- MPC-inspired model-free branching DQN architecture;
- source provenance and REUSE/ADAPT/EXCLUDE decisions.

## Source basis

- `fan2022powergym`
- `erazo2022model`
- `lee2022graph`

## Runtime boundary

No files under `src/`, `tests/`, or `pyproject.toml` are modified.

Controller implementation remains prohibited until the Day-2 P1 freeze is complete and the
required simulator-side contracts are available.
