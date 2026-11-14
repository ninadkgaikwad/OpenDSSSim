# P2 IEEE-123 restoration: ratified two-scenario experimental design (V01)

**Ratification date:** 2026-10-28  
**Authority:** User-ratified P2 demonstration scenario and feeder-topology design.  
**Status:** **DESIGN RATIFIED; native electrical qualification and numerical experiment freeze pending.**  
**Predecessor science:** `P2_ControlScience_Contract.json` and `P2_Reconfiguration_Restoration_ControlScience_FROZEN.tex` (Blocks 1–11 unchanged).  
**Predecessor engineered feeder:** `experiments/pesgm2027/feeders/ieee123_p2_restoration/`.  
**Preservation policy:** The original `ieee123_base`, existing `ieee123_pesgm2027` (P1 PV) and previous P2 candidate must remain unchanged. P2 has two explicit derivative circuit directories, rather than silently changing the common working feeder.

## 1. Purpose and scope of this ratification

Two complementary fixed-health, multi-fault demonstrations shall be developed for comparison of the frozen **reference/RBC, multiperiod MPC, and RL** P2 controller families. **MF01** demonstrates partial restoration with unavailable infrastructure. **MF02** demonstrates competition among multiple valid radial restoration routes. Both use the same IEEE-123 baseline family but each comparison is **within one scenario**: the three controllers must face an identical electrical feeder and realization within that scenario. Cross-scenario comparisons are descriptive, not apples-to-apples controller rankings because the equipment availability differs.

The ratification freezes the scenario *identities, health-down elements, switch endpoints and intended topology choices*. It does **not** freeze conductor corridors, impedance, protective ratings, final physical limits, load priority assignments, curtailability, time resolution, MPC horizon, or the learning/training setup.

## 2. Physical source and feeder lineage

| Directory | Role | Allowed modification |
|---|---|---|
| `experiments/pesgm2027/feeders/ieee123_base` | Immutable reference IEEE-123 | None |
| `experiments/pesgm2027/feeders/ieee123_pesgm2027` | P1 PV-augmented IEEE-123 | None |
| `experiments/pesgm2027/feeders/ieee123_p2_restoration` | Installed P2 eight-switch candidate | None |
| `experiments/pesgm2027/feeders/ieee123_p2_mf01_simple` | MF01 nine-switch derivative | Add Sw9 only |
| `experiments/pesgm2027/feeders/ieee123_p2_mf02_exotic` | MF02 eleven-switch derivative | Add Sw9, Sw10 and Sw11; split L78 at its far terminal, preserving its entire original line impedance |

Both variants preserve the IEEE-123 original 91 loads, 7 RegControls and 4 capacitors. Neither inherits the P1 10-PV addition. The predecessor P2 already has six normally closed controllable sectionalizers (Sw1–Sw6) and the real-bus normally open ties Sw7 (151–300, ABC) and Sw8 (54.1–94.1, A).

### Added physical switch candidates

| Device | From | To | Phases | Default | Function |
|---|---|---|---|---|---|
| Sw9 | bus 81 | bus 87 | ABC | Open | Alternative feed into L77-affected pocket; both variants |
| Sw10 | bus 72 | bus 89 | ABC | Open | Competing alternative route; MF02 only |
| Sw11 | L78 original bus 77 side via an inserted intermediate bus | bus 78 | ABC | Closed | Series sectionalizer permitting two ties to close without a cycle; MF02 only |

**L78 handling:** The physical L78 keeps `LineCode=6` and `Length=0.1` (and therefore its original line-impedance model); its former bus-78 terminal is changed to `P2SW11MID`. A separate, initially closed Sw11 connects that intermediate bus to bus 78. Do *not* replace L78 with an ideal switch. The initial master file uses explicitly stated, small switch-line impedances for Sw9–Sw11 as a qualification-stage engineering placeholder. These values are **not** ratified physical conductor specifications for geographically separated ties, and must be replaced/supplemented only through separate documented electrical design qualification.

## 3. MF01 — simple combined multi-fault resilience

**Health down:** `L45` (44–47, ABC), `L77` (76–86, ABC), `L93` (93–94, phase A), `Sw7` (151–300, ABC). All other elements healthy. Faults are already isolated before controller decisions; they remain unavailable for the complete evaluation. A health-down Sw7 may never be closed, even if doing so restores more nominal service. Initial controls: Sw1–Sw6 closed, Sw7–Sw9 open.

**Structural candidate action:** Close Sw8 and Sw9; Sw7 stays open/unavailable and Sw1–Sw6 remain closed. The static, phase-aware screen reports 76/91 loads (2,715 nominal kW) source-connected after fault isolation and 84/91 loads (2,975 nominal kW) after this restoration. The remaining 515 nominal kW is structurally unreachable in this candidate. This is *nominal source connectivity* and not power delivered or an optimality certificate under voltage/thermal constraints.

**Controller question:** Do all controllers honor fault availability, produce a structurally legal partial restoration and manage priority-weighted curtailment under operational limitations? We do not artificially manufacture a forecasting advantage for MF01.

## 4. MF02 — exotic route-selection challenge

**Health down:** `L45` (44–47, ABC), `L77` (76–86, ABC), `L93` (93–94, phase A). **Sw7 remains healthy** but initially open. Initial controls: Sw1–Sw6 and Sw11 closed, Sw7–Sw10 open. All health states fixed during each full evaluation horizon.

Three *bus-level radial, source-connected* configurations were found in the static screen. Sw7 and Sw8 are closed for all three:

| Choice | Sw9 (81–87) | Sw10 (72–89) | Sw11 (L78 series) | Switching changes from default | Static nominal source-connected load |
|---|---|---|---|---:|---:|
| A: via 81–87 | Closed | Open | Closed | 3 | 91/91, 3,490 kW |
| B: via 72–89 | Open | Closed | Closed | 3 | 91/91, 3,490 kW |
| C: split L78 | Closed | Closed | **Open** | 5 | 91/91, 3,490 kW |
| **Invalid** | Closed | Closed | Closed | 4 | Bus-level cycle; MUST reject |

The three valid choices differ in network routing and switching effort. They may differ in unbalanced voltage, thermal loading and losses, but that has **not** been demonstrated by native AltDSS. C should not be presumed better: it costs two more switching operations than A/B, and must justify them with a measurable operational benefit.

For context, the prior static enumeration of the *virtual-switch* model tested 2^11 = 2,048 switch combinations, finding 1,792 bus-level radial configurations, 256 cyclic configurations, and 6 radial configurations connecting all 91 nominal loads. These counts serve only as a structural parity reference; the installed eleven-switch circuit and exact split of L78 require independent native qualification.

## 5. Controller-science interpretation

- **RBC/reference:** Deterministic current-state graph search, healthy-path feasibility and controller-side electrical evaluation; priority-aware curtailable-service decoder. No future information is supplied to RBC.
- **MPC:** Forecast-based multiperiod MILP with multiphase unbalanced LinDistFlow, binary switch topology decisions, service/curtailment, radiality/source-connectivity and operational-voltage/thermal constraints. Hard structural conditions have no slacks.
- **RL:** Stable-Baselines3 custom masked DQN selects a topology catalogue entry, then uses the same deterministic reference/RBC curtailment decoder. RL does not directly choose independent unconstrained switch bits.

The **common objective hierarchy** from frozen science is operational feasibility/violation first, then priority-weighted service, switching effort, then optional voltage-profile tie-break. No scientific mathematics or RL backend is modified here.

MF02 offers a *testable hypothesis*: under a common time-varying load realization, the best present-state route need not be best across a forecast horizon. MPC may proactively select another route or alter curtailment, RBC may react when limits materialize, and RL may generalize to previously experienced patterns. **It is not acceptable to claim any such advantage until all three controllers are run and all actions evaluated through the same authoritative OpenDSSSim/AltDSS plant.**

## 6. Fairness and persistence contract

For any chosen scenario `j`, require the same `Ω_j` across reference, MPC and RL: feeder and electrical parameters; health mask; initial switch state; source; per-phase load trajectory; priority labels; curtailability declarations; voltage and thermal limits; control timestep; evaluation horizon; and plant realization. MPC and RL receive exactly the same forecast (with any uncertainty policy shared); RBC observes only present information. All controllers run the entire test horizon; they never terminate early merely because restoration was initially successful. Compare realized plant voltage/thermal performance, priority-weighted unserved energy, unserved energy normalized to structural availability, switching count, curtailable service, operation slacks and control runtimes. RL official test exploration epsilon=0. Only RL uses TRAIN and TEST partitions (no validation split or HPO in the frozen protocol).

A standalone native AltDSS fixture is valid for *pre-controller circuit qualification*. Official controller comparisons must submit commands via `env.step(a_req)`. Neither controller nor orchestrator may mutate the authoritative plant directly, and the plant must not silently repair controller actions.

## 7. Native electrical qualification and experiment freeze gates

**Gate E0 — package/source:** fail-closed repository predecessor hashes, new-feeder source reproducibility and static fault/topology parity.

**Gate E1 — native compile/solve:** independently compile MF01 and MF02 in AltDSS, verify initial states and all switch/line endpoints, physically isolate health-down elements, attempt the listed structurally admissible actions, check solver convergence and compute per-phase voltage and branch-loading summaries.

**Gate E2 — physical design:** source evidence for actual Sw9/Sw10 tie-corridor impedances and ratings (or defensible IEEE-123 synthetic additions), phase compatibility, L78 split correctness, source and regulator response, plus voltage/thermal feasibility under a representative load envelope. If these fail, revise equipment *without rewriting the frozen P2 science*; document variant V02 rather than overwriting a ratified V01 artifact.

**Gate E3 — experiment numeric freeze:** ratify load priority classes 1–4, subset of controllable curtailable loads, forecast design, load trajectories, limits, timestep, MPC horizon, reference-controller electrical evaluator, RL topology catalogue/masks/reward/seed count, common scoring/plots. Preserve frozen P2 objective and no structural slacks.

**Gate E4 — comparative qualification:** RBC, MPC and RL use the same scenario j, initial state and full horizon. Assess realized plant-level outcomes; failure/fallback uses controller-side last-successful action, with explicit logging.

**Controller implementation remains on hold until OpenDSSSim v1 is complete and formally qualified.** Creating these independent experimental feeder files and documentation does not lift that gate.

## 8. Ratification versus outstanding scientific decisions

**Ratified here:** two scenario identities (MF01 simple, MF02 exotic); fault masks; Sw9 81–87 ABC, Sw10 72–89 ABC, Sw11 in-series L78; separate derivative P2 feeders; the three planned exotic route cases; graph-only parity values and hard structural rejection; P1/base/P2-predecessor preservation.

**Not yet ratified or qualified:** final tie electrical data, switch ampacity/protection constraints, AltDSS AC feasibility/convergence, whether paths A/B/C actually provide different useful operational tradeoffs, numerical load/priority/curtailability/forecast choices, official metrics and training/testing realization. Do not state that either scenario is electrically or controller-science performance qualified.
