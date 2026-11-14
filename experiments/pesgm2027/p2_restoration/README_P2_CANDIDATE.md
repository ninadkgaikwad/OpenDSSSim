# P2 IEEE-123 minimal demonstration feeder — engineering candidate V01

This is a **separate, additive** P2-only experiment feeder. It is NOT a
controller implementation, not an OpenDSSSim v1 source patch, and not a
ratified experiment-science freeze. No P1 PV systems are inherited.

## Physical circuit

- 91 original loads, 7 original RegControls, 4 original capacitors, all
  original line/regulator/load definitions (except the 8 switch declarations).
- 6 source closed inline switches, 2 source normally-open tie switch locations.
- `Sw1`--`Sw8` now explicitly declare `Switch=Yes` **before** original
  `r1,r0,x1,x0,c1,c0,Length` parameters, to retain original values.
- `Sw7`: `151` to `300` (3-phase); `Sw8`: `54.1` to `94.1` (A only).
- At circuit compilation, explicit `Close Line.Sw1..Sw6 1` and
  `Open Line.Sw7 1`, `Open Line.Sw8 1` precede voltage-base solve.
- No new devices, no `SwtControl` or automatic switching logic.

## Scenario screen

`P2_STATIC_SCENARIO_SCREEN.csv` reports **load-terminal phase connectivity only**;
regulator winding phase channels are approximated as same-phase connectivity
and the delta-connected secondary is abstracted to phase correspondence.
These are NOT AC feasibility results and not a phase-angle/protection assessment.

`validate_p2_candidate_altdss.py` is a **separate native-solver smoke test**.
It runs snapshots in isolated AltDSS contexts, checking source switch states,
external post-fault isolation and native convergence. In particular, it does
NOT certify voltage, thermal loading, regulator operation, fault current,
protection coordination, or actual energy served. Scenario fault branch openings
are external health/isolation preconditions, **not controller actions**.

After installation, run static source-integrity and then native-AltDSS checks from repository root in the locked environment:

```
python -B experiments/pesgm2027/p2_restoration/validate_p2_candidate_static.py
python -B experiments/pesgm2027/p2_restoration/validate_p2_candidate_altdss.py --out "$HOME/Downloads/P2_Feeder_NativeQualification"
```

The independent official P2 implementation and final scenario/limits/priorities
will follow only after OpenDSSSim v1 freezes. NEVER promote the native snapshot
smoke evidence into official controller-comparison results.

## Freeze exceptions / scope

A predecessor source note prescribed one shared P1/P2 working feeder, while the
frozen P2 science contract explicitly defers the working copy. This P2-only
candidate is a proposed, reversible experiment asset; user ratification required
before declaring the final feeder frozen. It does not mutate the older shared
P1 working directory.

**Hard radiality:** the native harness intentionally rejects the cyclic S05 scenario BEFORE sending switching commands to AltDSS.
