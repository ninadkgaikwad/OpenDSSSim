# OpenDSSSim PESGM-2027 External-PQ Native-Control Scalability Contract V02

## Objective

Run the same externally driven 8760-hour load trajectory through three immutable
baseline distribution circuits using only already-qualified OpenDSSSim capabilities.

Baseline ladder:

1. `ieee123_base`
2. `ieee906_european_lv_base`
3. `ieee8500_base`

## External load truth

The packaged file `truth_load_multiplier_8760.csv` has exactly 8760 hourly rows.

It is generated from a fixed 24-hour daily curve, normalized to mean 1.0, repeated
for 365 days, with additive Gaussian noise:

- seed: `8760`
- sigma: `0.02` pu
- clipping: `[0.65, 1.3]`
- CSV SHA256: `2E4447CE612E1ECBFBC891F5A75F23F67AC7C11AF40E9FAAA75491CB5DC0BD2C`

The exact same multiplier `m_t` is applied to every load on every feeder.

OpenDSSSim A05 `ReplayBinding(..., mode="multiplier")` performs:

`P_i,t = m_t P_i,0`

`Q_i,t = m_t Q_i,0`

Therefore each load retains its own native baseline power factor and kvar sign at all
times. No separate Q noise is introduced.

## Native controls

The ProblemSpec has:

- native control authority;
- empty external ActionSpec;
- observations: solution convergence and all bus per-unit voltages.

`NativeControlsBaseline` therefore returns the authorized empty action. Physical native
controls remain inside OpenDSS/AltDSS.

## Debug persistence

The official requested history level is `HistoryLevel.H3`, the highest available
OpenDSSSim history level.

H3 includes:

- requested/applied/realized actions;
- internal state;
- disturbances;
- parameters;
- constraints;
- availability;
- authority;
- solution;
- full state;
- info, including A05 replay provenance.

Because IEEE-8500 H3 is intentionally large, each H3 record is streamed immediately to
`debug_history_H3.jsonl.gz`, then the public `RuntimeHistory.clear()` method is called.
This bounds Python history retention while preserving the exact H3 record on disk.

The 3-step pilot must be reviewed before the 8760 run. The pilot summary estimates
full-run compressed H3 size and wall time.

## Timing

Per step, the experiment records:

- controller-context time;
- controller action time;
- full `env.step()` wall time;
- native AltDSS `SolutionResult.process_time_s`;
- `env.step - process_time` as combined OpenDSSSim framework + A05 + observation + H3
  overhead;
- H3 gzip serialization time outside `env.step`;
- total loop wall/CPU time;
- solver/control iterations;
- memory;
- P/Q at the feeder head;
- exact load multiplier and replay row.

No private simulator timing hook and no direct AltDSS mutation are used.

## Evidence ancestry

Fresh tree SHA256:

`086471EA16188938E97BBC74BE7C49A9ECAEC1CF09C3C378C344463732E31288`

Directed source SHA256:

`A690FD7A731BF236991ED9EB1DAC2BA13A6C3A9B176EF4C413C36BC09F9087C6`

Directed files independently verified:

`287`

OpenDSSSim source modified by this patch: **NO**.

Existing feeder baseline files modified by this patch: **NO**.
