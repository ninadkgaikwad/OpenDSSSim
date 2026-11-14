# P2 IEEE-123 MF01 — ratified demonstration topology

- Design ratified 2026-10-28; **not** yet electrically qualified or frozen for official experiments.
- Parent: installed `ieee123_p2_restoration` feeder (source hash pinned in the install manifest).
- Full independent feeder copy with all DSS redirects kept local.
- No changes to IEEE-123 reference, P1, or previously installed P2 candidate.
- Switch additions: Sw9 81-87 ABC, initially OPEN.
- Model health-down branches through experiment setup, **not** by permanent feeder edits.
- The added ties are low-impedance switch-line placeholders without qualified physical corridor length, ampacity, or impedance. Do not claim native electrical feasibility before qualification.
- For MF02, L78 remains `LineCode=6 Length=0.1`; its far terminal is relocated to `P2SW11MID` and a separate `Sw11` spans that mid bus to physical bus 78.
- Do not use direct `altdss` mutation in controller code; standalone electrical screening scripts may independently compile the circuit. Official controls must go through `env.step(a_req)` after OpenDSSSim v1 freeze.
- Source master: `IEEE123Master.dss`.
