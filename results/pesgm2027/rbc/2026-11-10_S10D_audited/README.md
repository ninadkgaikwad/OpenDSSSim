# OpenDSSSim PESGM2027 — RBC P1/P2 independently audited evidence

Audit date: **November 10, 2026**  
Status: **PASS evidence integrity / native voltage pilot**; **NOT full P2 science qualification**.

## Verified scope

- **S10D source:** 331-file qualified S09A predecessor, one controller-only replacement (`p2_graph.py`), two additive docs/tests, expected 333-file successor; all 56 separate P2 assets preserved. Reconstructed SHA-256 successor: `0C4887E12C8B81D7E243590DBE043B7BD8EC2E7156861B4024B1969840400797`. Installation source integrity is reported by the native verifier; an actual fresh post-S10D 333-file tree has not yet been externally reviewed.
- **Qualification:** 5 P2 graph tests; 3 S09 RBC rule tests; 3 public native-contract tests; 8 B00 native tests; three full pytest regressions each with 241/241 passing. Seven standalone test log hashes recomputed and matched. **R01 still open** because Windows native-exception diagnostics (`0xe0465043`) appear in stderr despite successful pytest exits.
- **Result integrity:** 34/34 S10D P2 archive members verified against standalone SHA-256/byte manifest, exact ZIP integrity, identical scientific data in embedded/standalone receipts. P1 original archived results and manifest also passed re-verification.

## P1 results (synthetic diagnostic)

- **24 sequential RBC actions / 25 converged samples.**
- Exploratory 0.95–1.05 pu bus-phase band: native baseline **0** out-of-band counts, RBC **133** accumulated out-of-band counts.
- RBC minimum **0.941698 pu**, maximum **1.026532 pu**.
- **Do not claim RBC improves voltage over native:** controller authority differs (native automatic regulator vs external regulator control); trace timestamps are not identical, even though sample indices are aligned. The profiles are synthetic rather than field data.

## P2 candidate voltage screens (all converged)

| Case | Source-connected nominal kW | Switching changes | Vmin (pu) | Vmax (pu) | Band violations | Selected? |
|---|---:|---:|---:|---:|---:|---|
| MF01_RATIFIED_PARTIAL | 2,975 | 2 | 0.979918 | 1.049791 | 0 | Yes |
| MF02_ROUTE_A | 3,490 | 3 | 0.972454 | 1.047376 | 0 | Yes |
| MF02_ROUTE_B | 3,490 | 3 | 0.972336 | 1.050582 | 1 | No |
| MF02_ROUTE_C | 3,490 | 5 | 0.972312 | 1.047709 | 0 | No |

MF01 restores **84/91 structurally connected loads** and **2,975 kW** of nominal load in its ratified partial route; MF02 Routes A/B/C all supply **3,490 kW** nominal. **MF02 Route B** has 1 over-voltage bus-phase at 1.050582 pu; Route A and Route C have 0. A (3 switching changes) was selected over C (5 changes).

## P2 live native pilot

Both selected routes issued **2 sequential native steps** and converged, with **0 out-of-band energized bus-phases** in each live trace. The switch `live_action_audit_step{1,2}.json` files and native recorder CSV are in the results ZIP. MF01 includes 18 de-energized/zero phases as recorded and must not treat them as a voltage-pass on energized load.

## Scientific boundaries — must appear in PESGM write-up

1. Missing conductor/switch ratings mean **thermal limits are NOT assessed**.
2. Equal load priorities are illustrative, not utility-validated; no curtailable load was declared, so **priority/curtailment optimization was NOT exercised**.
3. Radiality is checked on a bus graph, not a formal phase-aware proof.
4. Candidate screening uses one native electrical snapshot; the two repeated live steps are **not** a resilience time series or disturbance trajectory.
5. These are experimental RBC reference pilots, **not globally qualified optimal restorations or fully constrained MPC/RBC benchmarks**.
6. Voltage comparisons must disclose synthetic profiles and controller-authority differences.
7. Reliability diagnostics **R01 OPEN**, **R02 OPEN_MITIGATION_QUALIFIED** remain unchanged.

## MPC implementation gate

MPC code has **not** been installed or qualified. The new MPC P1/P2 implementation requires a **fresh full 333-file repository tree, independent review, then directed-source capture and review** before any patch. Begin from existing frozen P1 LinDistFlow and P2 switching MILP/Gurobi contracts; do not modify qualified simulator/feeder physical source. Match the P1 synthetic inputs and P2 ratified circuits, capture native benchmarks alongside new MPC trajectories, and avoid unverified thermal/priority claims.

## Evidence chain (original unmodified artifacts)

- `evidence/RBC_S10C_Results_20261110T212402030029Z.zip`: P1 24-step native vs RBC trace + original earlier S10C P2 failure retained for provenance.
- `evidence/RBC_S10D_P2_Results_20261110T224009892176Z.zip`: accepted P2 MF01/MF02 experimental candidate and live native traces.
- `evidence/RBC_S10D_Qualify_20261110T222533634405Z_Evidence.zip`: all 7 hash-verified test logs and immutable expected successor manifest.
- `evidence/RBC_S10D_Pilot_20261110T224005116782Z_Evidence.zip`: P2 native runner log and qualification references.
- Exact cryptographic hashes, all check IDs, and original receipt provenance are in `RBC_S10D_IndependentAudit.json`.
