# Input and evidence provenance

The GitHub release was assembled from `OpenDSSSim.zip` (the user-uploaded repository snapshot), with **no executable frozen simulator changes**. Its educational inputs were copied byte-for-byte from original source feeders and previously qualified research packages present in the same OpenDSSSim project.

| Resource | Source | Verification |
|---|---|---|
| IEEE-123 base, P1, MF01, MF02 feeders | Original `experiments/pesgm2027/feeders/` in uploaded `OpenDSSSim.zip` | Per-file input SHA-256 + original upstream license files |
| A07A2 MPC static cases | `MPC_A07A2_24Steps.zip`, `baseline/cases` | Original `CASE_PINS.json`; source master SHA matches repo circuits |
| RBC selected routes | `P2_RBC24_Run.zip` pinned S10D evidence | Original S10D archive SHA-256 `E2B37D6D7EB18E378497B32606F34433BF23B99F7D20AF8FBE4929BF5A14C4F0` |
| Diagram coordinates | Audited `PESGM_Writer_V06.zip` | Diagram coordinate provenance included; not geodetic |
| Archived paper comparison CSVs | Audited `PESGM_Writer_V06.zip` | Clearly labeled reference results, not new generated runs |

The source master hashes match the A07A2 qualified static captures, so the copied feeder inputs do not introduce a new circuit physics model. The `input/SHA256_INPUT_MANIFEST.csv` records every bundled immutable example input. The offline package construction did not independently execute AltDSS or Gurobi.

**Copyright and redistribution:** The IEEE-123 DSS files retain `OpenDSS_License.txt`; original source provenance also remains in `experiments/pesgm2027/feeders/`. Review those terms and rights to redistribute downstream reference evidence before making the repository public. No project-wide open-source license is inferred from the presence of an IEEE feeder license.
