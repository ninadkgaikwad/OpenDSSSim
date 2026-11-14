# P1 RL Audit — Lee et al.

**Status:** DAY-1 SOURCE AUDIT COMPLETE  
**Primary source:** Lee, Sarkar, Wang, *A graph policy network approach for Volt-Var Control in power distribution systems*, Applied Energy 323 (2022) 119530.  
**BibTeX key:** `lee2022graph`  
**Provided PDF:** `1-s2.0-S0306261922008479-main.pdf`

## A. Source and provenance

The uploaded full text was audited for RL observations, device/action spaces, policy
architecture, reward basis, IEEE-123 case-study devices, and conventional-controller
comparison.

## B. SOURCE — reusable science

Lee et al. builds on the PowerGym VVC problem and uses:
- voltage regulators;
- capacitors;
- batteries;
- voltage/device-status observations;
- a multi-discrete action structure;
- PPO-based dense and graph policy variants;
- a reward based on the same VVC physical objective family.

For its 123Bus case study, the source reports four capacitors, four voltage regulators,
and four batteries, with the resulting voltages shown within 0.95–1.05 p.u.

The paper also studies actuator influence and reports that regulator effects are more
global while capacitor/battery effects are more local.

## C. SOURCE limitation relevant to our benchmark

The source RL policy uses current observations; it does not provide the future
load/PV forecast tensor planned for OpenDSSSim.

Its primary RL algorithm is PPO/Graph-PPO, not DQN.

PV inverter control is not part of its P1 device set.

## D. ADAPT

OpenDSSSim P1:
- replaces batteries with PV-inverter reactive-power control;
- gives RL the same authorized load/PV forecast tensor as MPC;
- uses branching/factorized DQN rather than PPO;
- controls 10 regulator, 10 capacitor, and 10 PV-Q channels simultaneously;
- derives the reward from the common MPC stage-cost semantics.

## E. RBC clue

The source discusses comparison with default OpenDSS VVC control and provides useful
evidence for local/conventional device-control baselines, but it does not supply the full
three-device RBC adopted by OpenDSSSim. The unified RBC remains an adaptation assembled
from conventional regulator, capacitor, and inverter Volt/VAR logic.

## F. Contribution to common P1

Lee supplies source support for:
- RL on the same VVC physical problem;
- multi-device discrete action challenges;
- topology-aware policy motivation;
- IEEE-123 regulator/capacitor/battery benchmark structure;
- conventional local-control comparison clues.

The final branching DQN is an OpenDSSSim benchmark design.
