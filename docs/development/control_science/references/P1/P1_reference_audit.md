# P1 Reference / Environment Audit — PowerGym

**Status:** DAY-1 SOURCE AUDIT COMPLETE  
**Primary source:** Fan, Lee, Wang, *PowerGym: A Reinforcement Learning Environment for Volt-Var Control in Power Distribution Systems*, L4DC 2022.  
**BibTeX key:** `fan2022powergym`  
**Provided PDF:** `fan22a.pdf`

## A. Source and provenance

The uploaded full text was audited for P1 physical problem definition, device vocabulary,
observation/action spaces, transition semantics, objective/reward terms, and benchmark
assumptions.

## B. SOURCE — reusable science

PowerGym frames Volt/VAR control as sequential control of voltage regulators, switchable
capacitors, and controllable batteries to reduce voltage violations and power loss while
penalizing device operation.

It defines:
- radial/multiphase distribution-network equations;
- discrete capacitor and regulator actions;
- discrete or continuous battery actions;
- voltage/device-state observations;
- a reward derived from voltage violation, controller-operation, and power-loss terms;
- a finite-horizon Gym-style interaction around OpenDSS.

The source uses the voltage band 0.95–1.05 p.u. in its VVC penalty construction.

## C. ADAPT

OpenDSSSim P1:
- separates full plant state `x_t` from authorized observation `o_t`;
- replaces battery control with PV-inverter reactive-power control;
- adds explicit requested/applied/realized action layers;
- uses 10/10/10 regulator/capacitor/PV control channels;
- allows forecast-aware RL for fair information access.

## D. EXCLUDE

Battery/SOC dynamics and terminal-SOC reward are excluded from P1 v1.

## E. Contribution to common P1

PowerGym supplies the strongest source basis for:
- the common VVC physical framing;
- regulator/capacitor device semantics;
- sequential Gym/OpenDSS plant interaction;
- voltage/switching/loss-style objective design.

It does not by itself provide the final OpenDSSSim RBC or MPC.
