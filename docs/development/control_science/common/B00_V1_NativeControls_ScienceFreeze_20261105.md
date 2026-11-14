# OpenDSSSim — B00 V1 Quasi-Static Native-Controls Baseline: Science Freeze

**Freeze decision:** ACCEPTED for the explicitly bounded B00 V1 quasi-static reference scope, effective 2026-11-05.  The corresponding repository documentation-only closeout is completed only after the guarded local installation succeeds and independent evidence is reviewed.

## Authority and source identity

- Qualified engineering baseline: B00I2R2, 264-file SHA-256 `AC91A34154084441E871C19C383AA35E248610A3ADCC60326A09CE36F7D3C446`.
- Separately tracked P2/experimental assets: 56 files, reference manifest SHA-256 `4A83C0F1AA903B0C6A59127263AFFFCBDB1D838DA2F582316AE4F64F04A7E945`; **these are not assimilated into the 264-file qualified source manifest**.
- B00I2R2 Windows qualification evidence ZIP SHA-256 `4594912F19A25EE1E2A458CBBABD1411688FFAFE61292749D5537B300452576C`.
- Verified native gates: queue unit 6/6, recorder/renderer unit 15/15, four-feeder native 4/4, B00I1 legacy 12/12, A05 legacy 99/99, three full regressions of 224/224 each; zero skips or JSONDecodeError reported.
- Four 24-hour native campaigns: 25 records per case (one reset plus 24 1-hour steps), 100 converged snapshots total; campaign seed 511 and `SYNTHETIC_DIAGNOSTIC_NOT_FIELD_DATA` provenance. The baseline uses one authoritative AltDSS solution per OpenDSSSim step and **no external supervisory action**.

## Ratified four-case baseline

| Case | Feeder directory | Baseline topology/controls | Measured 24-hour active losses |
|---|---|---|---:|
| Base | `experiments/pesgm2027/feeders/ieee123_base` | Native 7 regulator controllers, four as-installed capacitor banks | 1685.415 kWh |
| P1 | `experiments/pesgm2027/feeders/ieee123_pesgm2027` | Same native controls plus ten PV systems; no external Volt/VAR controller | 1434.613 kWh |
| P2 MF01 | `experiments/pesgm2027/feeders/ieee123_p2_mf01_simple` | Fixed MF01 PRE fault/topology; no restoration switching | 1112.117 kWh |
| P2 MF02 | `experiments/pesgm2027/feeders/ieee123_p2_mf02_exotic` | Fixed MF02 PRE fault/topology; no restoration switching | 1112.118 kWh |

P2 `ieee123_p2_restoration` is an older preserved candidate, **not** a fourth/current ratified experiment variant. Comparisons between distinct MF01/MF02 physical availability regimes are descriptive; controller rankings must be within each common scenario.

## Included, instrumented quantities

- Successful authoritative Snapshot solve with native `ControlMode=STATIC`, `MaxControlIter=10`, and seven enabled `RegControl` objects reported by B00 diagnostics, with native control-setting readbacks.
- Recorder-backed, versioned JSON and CSV plus self-contained offline HTML/SVG renderer output; feeder voltage summaries and energized-node violation counts, feeder P/Q, active and reactive losses, net tap-position-change proxies, capacitor/switch states, solver and control-iteration summaries, queue and event-log post-solve readbacks, profile provenance.
- P2 PRE disconnected/zero-voltage phases are **not** counted as healthy energized voltage violations. No P2 unserved-energy metric is provided by the B00 recorder and no restoration is commanded.
- Post-solve `QueueSize=0` and display `['No events']` were interpreted as a native sentinel rather than a pending action. Empty post-solve queues **do not** establish that no internal controller actions occurred.

## Explicit exclusions — NOT established by this freeze

1. Physical regulator timing, scheduled-event reconstruction, equipment wear, or exact mechanical tap-operation counts (the reported value is a **net-position-change proxy**).
2. Control effectiveness of P1 or P2 RBC/MPC/RL, physically realistic operator response latency, market operation, forecast advantage, or optimized restoration.
3. Claims based on field-validated utility demand/PV data. B00 uses synthetic diagnostic trajectories.
4. P2 feeder parameter redesign, conductor ampacity/thermal rating completion, new fault/outage events, new ties or load priorities. Preserve the ratified MF01/MF02 as installed.
5. Interpreting lower total P2 losses as superior service: P2 PRE has disconnected/unserved loads.

## Runtime source and authority boundary

The science freeze does not grant controllers direct AltDSS access or change A03/A04/A05 contracts. Future RBC, MPC and RL issue a configured requested action `a_req` through the same `env.step(a_req)` boundary. OpenDSSSim remains solely responsible for admissibility, applied action, native plant, realized state and audit. Native control and external supervisory authority must be deliberately configured to prevent double commands to the same regulator.

## Reliability open items

- `R01`: recurring native Windows `0xe0465043` trace: **OPEN**, despite test gates passing.
- `R02`: capacitor native JSON reliability: **OPEN, MITIGATION QUALIFIED**; zero JSON decoding errors in this campaign is not permanent closure.
- B00 V1 freeze is a scoped science reference and **not** an unrestricted production reliability approval.

## Development release sequence

**B00 frozen → RBC P1/P2 → MPC P1/P2 → RL P1/P2.** Before **each** implementation patch, the next chat must collect and independently inspect a *fresh* repository tree and directed source bundle from the newly installed predecessor, including all relevant frozen science documents. Every delivered patch is one self-contained ZIP; every local execution is one complete PowerShell block from repository root; all resulting receipts/evidence ZIPs/sha256 sidecars go to `C:\Users\ninad\Downloads`. A failed installed patch is left intact for forensic inspection (do not rerun installer or silently roll back).
