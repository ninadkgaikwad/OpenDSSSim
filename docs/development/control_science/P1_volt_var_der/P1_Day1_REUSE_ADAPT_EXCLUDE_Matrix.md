# P1 Day-1 REUSE / ADAPT / EXCLUDE Matrix

**Status:** DAY-1 RATIFIED PROVENANCE MATRIX  
**Date:** 2026-10-07

| Element | Day-1 decision | Basis |
|---|---|---|
| Volt/VAR control as common P1 task | REUSE | PowerGym / Lee / Erazo |
| Voltage-band objective/constraint | REUSE | all three P1 sources |
| 0.95–1.05 p.u. target band | REUSE | consistent P1 source setting |
| Regulator/tap control | REUSE | all three P1 sources |
| Capacitor control | REUSE | all three P1 sources |
| PV/inverter active/reactive capability | REUSE/ADAPT | Erazo source; simplified to fixed available P and controllable Q |
| Battery/storage | EXCLUDE | source-backed but intentionally removed from P1 v1 |
| Wind DG | EXCLUDE | Erazo source; unnecessary for simplified P1 |
| Conventional DG | EXCLUDE | Erazo source; unnecessary for simplified P1 |
| PV active-power dispatch/curtailment | EXCLUDE for v1 | simplify to pure Volt/VAR |
| Load/PV forecasts | REUSE/ADAPT | Erazo forecasted operation |
| Forecast-aware RL | ADAPT | Lee source uses current observation; common benchmark gives RL same forecast view as MPC |
| Rule-based three-device coordination | ADAPT | assembled from conventional device-control logic |
| LinDistFlow internal prediction | ADAPT | simplified controller model |
| Gurobi MIQP MPC | ADAPT | chosen implementation form |
| Same physical cost semantics for MPC/RL | ADAPT | common benchmark design |
| Branching/factorized DQN | ADAPT | required to avoid combinatorial flat joint action |
| 10/10/10 controllable channels | NEW EXPERIMENT CONFIGURATION | OpenDSSSim benchmark choice |
| `a_req -> env.step -> AltDSS` | OPENDSSSIM SOFTWARE CONTRACT | framework boundary |
| IEEE-123 exact object names/locations | UNRESOLVED | Day 2 experiment design |
| Final control interval/horizon | UNRESOLVED | Day 2 |
| Final fixed weights | UNRESOLVED | Day 2 |
| Exact RBC thresholds/curves | UNRESOLVED | Day 2 |
| Exact branching-DQN training equations | UNRESOLVED | Day 2 |
