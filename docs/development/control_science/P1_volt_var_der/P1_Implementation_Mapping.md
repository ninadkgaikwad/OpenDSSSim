# P1 — OpenDSSSim Implementation Mapping

**Status:** DAY-2 CONTROLLER-MATH RATIFIED / REAL INTEGRATION PENDING

## Cardinality-general requirement

No RBC, MPC, or RL source may assume fixed numbers of regulators, capacitors, PV systems,
phases, buses, or IEEE-123 object names.

## RBC inputs

Each configured device channel receives:
- local monitored voltage channel set;
- configurable reduction rule;
- current realized device state where needed;
- device capability/parameter data.

PESGM multiphase RBC monitor reduction: `AVG`.
No controller delays are used in the experiment.

## MPC model-service inputs

The controller requires a read-only non-mutating model service that can supply:
- radial parent/child topology;
- active phase sets;
- branch impedance/coupling data;
- source/slack voltage;
- load/PV forecast mappings;
- regulator tap metadata and tap-voltage linearization coefficients;
- capacitor ratings/device-to-phase mappings;
- PV ratings/device-to-phase mappings.

The controller constructs/consumes LinDistFlow matrices without importing or mutating
AltDSS.

## RL implementation

BDQ is not available as a native Stable-Baselines3 2.8.0 algorithm. Implement the
branching Dueling Double DQN in PyTorch. Reuse generic SB3/SB3-like primitives only where
they do not change the algorithmic contract.

A trained checkpoint is dimension-specific even though the training pipeline is
cardinality-general.

## Common plant boundary

All paradigms emit `a_req`.

Only OpenDSSSim owns:
`a_req -> admissibility/application -> a_applied -> AltDSS solve -> a_realized`.

All physical transitions occur through one `env.step(...)` per control interval.
