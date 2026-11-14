# MPC A07A3 — P1 native capacitor-bank cardinality repair

**Scientific basis:** A07A3 fresh-tree ZIP, directed-source 210-file evidence,
P1 ratified mathematics (`P1_Optimization_Controller.md` and
`P1_VoltVAR_DER_ControlScience_FROZEN.tex`) and native IEEE-123 equipment.

**Root cause:** `Capacitor.C83` is one 3-phase/600-kvar bank, with phase injections
of 200 kvar each. The predecessor P1 solver inadvertently created three
independent switch binaries and three switching-effort auxiliaries per step
for this one physical capacitor channel. The public ProblemSpec exposes one
bank switching action. The A07A2 action adapter correctly rejects a solution
such as (1,0,1), before any `env.step` is made.

**Controller-side mathematical repair:** for every `P1Cap` physical entity
`c` and prediction index `k`, create ONE binary `b[c,k]`. Use its value
for every phase-specific reactive-power injection `qcap[c,j,k]=kvar[c,j]*b[c,k]`.
Switch effort has ONE auxiliary `z[c,k] >= |b[c,k]-b[c,k-1]|`, anchored
to the shared bank's current physical state at the first step. A disagreement
among initial phase states fails closed before optimization. The solver output
retains the existing ordered phase tuple, with its one optimized bank decision
repeated for the physical phases solely for backward compatibility with the
unchanged A07A2 action encoder. No post-solve voting/projection is allowed.

**Scope:** replace only controller-side `src/opendsssim/controllers/mpc/p1_miqp.py`;
add a regression test and this implementation note. No frozen simulator,
Plant/backend/registry, IEEE-123 feeder, P2 controller, science contract,
A07A2 encoder, or action authority modification.

**Scientific limits:** approximate LinDistFlow versus authoritative nonlinear
AC; voltage slack/weights unchanged; initial P1 feeder may have pre-existing
voltage excursions. Replaying 24 constant synthetic hourly samples does not
constitute a measured 24-hour profile or the 5-minute P1 science timestep.
Native 24-step Gurobi+AltDSS results remain to be established independently;
there is no claim of improved performance, solver optimality, or thermal
security until native receipts are audited.

**Mandatory gates:** exact 506-file predecessor; Verify; Install; Qualify
(including 15 previously ratified isolated tests, A07A3 tests and native
Gurobi 12-horizon solver check); independent review; then exploratory P1 Pilot
24 steps through existing official `env.step`, evidence in Downloads.

**Rollback:** `-Mode Rollback` accepts only the exact post-install successor,
restores the pinned original controller file, and removes only the two files
this package added. It never touches other source and refuses drift.
