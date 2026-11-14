# OpenDSSSim_ControllerScience_Day2_P1_FullMathContract_v01R1_20261010

**Status:** P1 controller-mathematics contract  
**Date:** 2026-10-10  
**Runtime source modified:** NO

## Purpose

Replace the Day-1 P1 pre-freeze mathematical scaffold with the complete detailed
controller-mathematics contract ratified through Day 2.

The TeX now contains:
- common cardinality-agnostic P1 plant/action/information contracts;
- complete local RBC equations and PESGM default numerics;
- exact single-phase DistFlow starting equations and derivation relationships;
- lossless LinDistFlow approximation;
- explicit PV-Q, capacitor, and regulator insertion into LinDistFlow;
- regulator tap-ratio linearization and persistent tap-state dynamics;
- multiphase phase-aware LinDistFlow/mapping form;
- explicit Gurobi-compatible MIQP variables, bounds, slacks, and switching auxiliaries;
- MPC-inspired model-free BDQ state/action/reward/Q/target/loss equations;
- explicit Stable-Baselines3 2.8.0 implementation boundary.

## Scientific boundary

P1 controller mathematics are ratified.

The final PESGM experiment freeze still requires:
1. exact IEEE-123 device placements/ratings/phase mappings;
2. one fixed numerical common-cost weight tuple after scale verification;
3. RL training-budget/hyperparameter qualification;
4. LinDistFlow-vs-OpenDSS validation on the selected feeder.

No controller runtime implementation is introduced by this patch.
