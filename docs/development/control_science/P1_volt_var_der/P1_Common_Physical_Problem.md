# P1 — Common Volt/VAR + DER Physical Problem

**Status:** DAY-2 CONTROLLER-MATH RATIFIED  
**Date:** 2026-10-10  
**Implementation:** NOT YET AUTHORIZED; exact IEEE-123 experiment mapping remains to be frozen.

## Common problem

P1 is a centralized Volt/VAR coordination problem executed on one OpenDSSSim plant.
The controller implementation is cardinality-agnostic. Let:

- `R` = regulator/tap control channels;
- `C` = capacitor control channels;
- `P` = PV-inverter reactive-power control channels.

The controller equations use arbitrary `|R|`, `|C|`, and `|P|`. The PESGM experiment
is expected to instantiate 10/10/10 channels, but no algorithm may assume those values.

Common exogenous quantities:
- active load `P^L`;
- reactive load `Q^L`;
- available PV active power `P^{PV,av}`.

PV active power follows availability. PV reactive power is controllable.

Common requested action:
`a_req = [Delta tau, c_cmd, q_PV_cmd]`.

Common desired voltage range:
`0.95 <= |V| <= 1.05 p.u.`.

Common experiment timing ratified from the Erazo source:
- control interval: 5 minutes;
- forecast/MPC horizon: 12 steps = 1 hour.

MPC and RL receive the same authorized current information and forecast tensor.
RBC is defined by local current-state logic and does not use forecasts.

All three controllers ultimately apply their complete requested action through one
`env.step(...)` call. Only MPC owns an internal LinDistFlow prediction model.
