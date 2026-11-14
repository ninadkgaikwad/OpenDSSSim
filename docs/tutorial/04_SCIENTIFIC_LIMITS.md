# Tutorial 4 — Scientific validity and publishing claims

The following are deliberate distinctions, not bugs to conceal in plots:

| Observed outcome | What you may claim | What you may NOT claim |
|---|---|---|
| Gurobi `OPTIMAL` | Solver satisfied its optimization stopping criterion | Exact global optimum beyond configured tolerances, or AC validity |
| Native AC `converged` | Snapshot solver converged for the applied state | Thermal security, voltage compliance, safe utility switching |
| Native voltages inside 0.95–1.05 | No violations of that **exploratory** band among energized observed components | All possible operating constraints passed |
| `ADMISSIBLE_APPLIED` action | Action admitted/applied through published contract | Realized capacitor state necessarily equals requested state |
| Graph connected kW | Nominal load connected to source according to a bus-level graph | Metered AC delivered real power or customer continuity |
| 24 RBC P2 steps | Selected S10D route held and structurally rechecked over 24 steps, validated in AC each step | New independently electrically optimized RBC route each hour |
| 24 MPC P2 steps | New Gurobi receding-horizon optimization at each step through official API | Fully accurate LinDistFlow, certified thermal ratings |
| Model P2 weighted unserved objective | Receding-horizon modeled priority-weighted energy metric with `dt_hours=0.25` | 24h realized energy, unless separately measured and aligned |
| P1 RBC vs MPC envelopes | Their respective qualified setups yield those measured envelopes | Exact apples-to-apples performance under identical initial/control conditions |

**Native voltage component indexing:** `bus_voltage_pu` may have a variable number of observed components per bus. The examples export `component_index` rather than guessing physical A/B/C label; source/phase mapping needs explicit native circuit metadata.

**P2 radiality:** the existing RBC graph uses a bus-level projection and special treatment of disjoint-phase regulator corridors. It does not constitute independent phase-aware radiality certification.

**P2 load:** source-connected nominal kW may differ from measured power due to losses, islanding, actual voltage-sensitive loads and other physical effects. The training outputs are clearly named `nominal_connected_kw_proxy`.

**Geography:** IEEE-123 coordinates are diagram coordinates and cannot be presented on a geographic basemap.

**RL:** the repository does not contain a qualified end-to-end Branching Dueling Double DQN implementation. Do not advertise an executable RL controller example from this snapshot.

**Scope:** this is a research and teaching framework. It has not been independently certified for field protection, dispatch, cyber-security, or life-safety operations.
