# P1 — LinDistFlow MIQP Model Predictive Controller

**Status:** DAY-2 MPC MATHEMATICS RATIFIED  
**Solver family:** Gurobi-compatible MIQP

The MPC uses a controller-side radial multiphase LinDistFlow approximation while the
authoritative plant remains OpenDSSSim/AltDSS.

## Exact single-phase DistFlow starting point

For branch `i -> j`, with `v_i = |V_i|^2` and `ell_ij = |I_ij|^2`:

`P_ij = p_j + sum_m P_jm + r_ij ell_ij`

`Q_ij = q_j + sum_m Q_jm + x_ij ell_ij`

`v_j = v_i - 2(r_ij P_ij + x_ij Q_ij) + (r_ij^2 + x_ij^2) ell_ij`

`v_i ell_ij = P_ij^2 + Q_ij^2`

The equations follow from `V_j = V_i - z_ij I_ij` and `S_ij = V_i I_ij^*`.

## LinDistFlow approximation

Neglect loss/current-squared terms:

`P_ij = p_j + sum_m P_jm`

`Q_ij = q_j + sum_m Q_jm`

`v_j = v_i - 2(r_ij P_ij + x_ij Q_ij)`.

## Device embedding

PV active power is fixed to forecast availability:

`p_j = p_j^L - p_j^{PV,av}`.

PV inverter reactive control enters net reactive demand:

`q_j = q_j^L - q_j^{PV} - q_j^{cap}`.

For capacitor channel `c`:

`q_c^{cap} = qbar_c c_c`, with `c_c in {0,1}`.

PV capability:

`-Qmax_p <= q_p^{PV} <= Qmax_p`

with

`Qmax_p = sqrt(S_p^2 - (P_p^{PV,av})^2)`,

precomputed from forecast quantities at each horizon step.

## Regulator model

For ideal ratio `a`, squared voltage transforms as `v_after = a^2 v_before`.
The tap ratio is parameterized around nominal:

`a(tau) = abar + Delta_a (tau - taubar)`.

A first-order linearization of `a^2 v` about `(abar,vbar)` gives an affine tap-voltage
contribution. Around nominal `abar ~= 1`, `vbar ~= 1`, this becomes

`a^2 v ~= v + kappa (tau - taubar)`,

with `kappa ~= 2 Delta_a`.

Tap position has actuator-state dynamics:

`tau_{r,k} = tau_{r,k-1} + Delta tau_{r,k}`,

`Delta tau_{r,k} in {-1,0,+1}`,

and `tau_min <= tau_{r,k} <= tau_max`.

## Multiphase form

Bus/branch quantities are phase vectors over the phases physically present.
Cross-phase coupling is retained through phase-aware matrices:

`v_j = v_i - R_ij P_ij - X_ij Q_ij + T_ij tau_ij`.

PV and capacitor device-to-phase mappings are supplied by circuit/model-service
incidence matrices. No controller equation assumes exactly three phases or fixed device
counts.

## MIQP structure

Decision variables across the horizon include:
- branch active/reactive flows;
- squared bus-phase voltages;
- PV inverter reactive power;
- binary capacitor states;
- integer regulator tap positions and incremental tap commands;
- nonnegative voltage slack variables;
- nonnegative switching auxiliary variables.

The objective is the sum of a common stage cost:
`ell = w_V J_V + w_sw J_sw + w_Q J_Q`.

The exact numerical weights are configuration parameters and are not tuned by Pareto
search in this project.

All first-step MPC requests are applied through the same `env.step(...)` interface as RBC
and RL. The LinDistFlow model never mutates the plant.
