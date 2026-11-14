# P2 Reconfiguration/Restoration Control Science Freeze

Patch: `OpenDSSSim_PESGM2027_P2_ControlScience_Freeze_v01R1_20261027`

This directory contains the frozen P2 mathematical/software contract consolidating
ratified Blocks 1--11.

## Authoritative file
`P2_Reconfiguration_Restoration_ControlScience_FROZEN.tex`

## Frozen controller families
1. Graph/reference restoration controller.
2. Multiphase LinDistFlow MILP MPC.
3. Stable-Baselines3 masked-DQN RL with deterministic priority-aware curtailment.

## Architecture
OpenDSSSim is the authoritative plant/state-health/action boundary.
Topology parsing, source identification, curtailability, operational limits,
LinDistFlow compilation, candidate evaluation, forecasts, topology catalogue,
action masking and controller logic are controller-side/orchestration concerns.

`env.step(a_req)` is the authoritative physical mutation boundary.

## Training/evaluation
Only RL has TRAIN/TEST partitions.
There is no VALIDATION partition and no HPO campaign.
Official comparison runs full closed-loop over the common evaluation horizon.
Every controller retains its last successful control computation for declared
controller-side fallback.

## Next stage
Implement P1/P2 controller classes and the controller-side orchestration/model layer
without changing the frozen science contracts.
