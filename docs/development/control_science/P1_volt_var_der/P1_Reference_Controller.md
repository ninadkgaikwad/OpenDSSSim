# P1 — Rule-Based Controller

**Status:** DAY-2 RBC MATHEMATICS RATIFIED

The P1 RBC is local, deterministic, simultaneous, and model-free.

For every controlled device channel `j`, monitoring is configurable through a reduction
operator

`V_mon,j = rho_j(V_channels,j)`,

where the generic implementation may support a configured phase selection and/or
`AVG`, `MIN`, `MAX` reductions as applicable. For the PESGM IEEE-123 experiment,
all multiphase P1 RBC monitors use `AVG`.

There are no controller delays in the P1 experiment. Every device evaluates its local
rule from the same timestep observation and all commands are concatenated into one
requested action before one `env.step(...)`.

## PV Volt/VAR

Generic curve parameters are configurable. The PESGM default curve is:

- `V <= 0.95`: `q/Qmax = +1`;
- `0.95 < V < 0.99`: linear ramp from `+1` to `0`;
- `0.99 <= V <= 1.01`: `q/Qmax = 0`;
- `1.01 < V < 1.05`: linear ramp from `0` to `-1`;
- `V >= 1.05`: `q/Qmax = -1`.

`Qmax = sqrt(S_rated^2 - P_PV_av^2)`.

## Capacitor voltage hysteresis

Generic ON/OFF thresholds are configurable.

PESGM defaults:
- ON at/below `0.97 p.u.`;
- OFF at/above `1.03 p.u.`;
- otherwise hold previous realized state.

No controller delay or dead-time logic is used in the experiment.

## Regulator deadband

Generic reference and bandwidth are configurable and expressed in per-unit, so the rule
is independent of feeder voltage level.

PESGM defaults:
- `Vref = 1.0 p.u.`;
- total band `B = 0.025 p.u.`;
- lower edge `0.9875`;
- upper edge `1.0125`.

Action:
- `+1` below lower edge;
- `0` inside band;
- `-1` above upper edge.

The sign convention is semantic: `+1` requests one tap step that raises the controlled-side
voltage and `-1` requests one step that lowers it.

The generic RBC never hard-codes IEEE-123 buses, phases, monitor names, device counts, or
the experiment numerical defaults.
