# Tutorial 6 — Citation, attribution and reproducibility

## Cite the repository/software

The active `CITATION.cff` and the root README contain **provisional software attribution**. Confirm the final software authors, copyright holder(s), repository URL, release tag, and commit SHA before making this repository public. The current development snapshot is `0.1.0a6`; no software DOI has been assigned in this package.

Provisional human-readable citation:

> OpenDSSSim contributors, *OpenDSSSim: A Generalized Gymnasium Framework for Distribution-System Simulation and Control*, research software v0.1.0a6 (2026). Include the GitHub repository URL, exact tag and Git commit when available.

BibTeX (replace provisional fields before publication):

```bibtex
@software{OpenDSSSim_v0_1_0a6,
  author  = {{OpenDSSSim contributors}},
  title   = {{OpenDSSSim}: A Generalized Gymnasium Framework for Distribution-System Simulation and Control},
  year    = {2026},
  version = {0.1.0a6},
  note    = {Research software; add verified repository URL, release tag and commit SHA.}
}
```

Once this project is pushed to GitHub, the repository's **Cite this repository** menu can use `CITATION.cff`. It does not replace the need to record the commit actually used for experiments.

## Cite the associated research separately

**Manuscript title (approved):** *OpenDSSSim: A Generalized Gymnasium Framework for Distribution-System Simulation and Control.*

**Status in the provided documentation:** IEEE PES General Meeting 2027 manuscript in preparation. No DOI, complete author list, proceedings pagination, or publication record has been supplied. Do not invent these. Once accepted and published, replace the provisional manuscript description with the authoritative IEEE citation and DOI and cite both the software and paper as appropriate.

## Minimum reproducibility information in a paper or issue report

Record:

1. OpenDSSSim version, release tag and exact Git commit SHA (`git rev-parse HEAD`).
2. Feeder variant: baseline IEEE-123, `ieee123_pesgm2027`, `ieee123_p2_mf01_simple`, or `ieee123_p2_mf02_exotic`.
3. Controller: RBC or MPC; for MPC, record horizon, solver version, tolerances and whether P2 uses original **slack-first** or sensitivity **service-first** objective ordering.
4. Number of post-reset steps and exact replay clock: 24 hourly AC steps are not identical to the static MPC case's `dt_hours=0.25`.
5. Qualified `ProblemSpec`, action/observation contract identities, authorized devices and fault-disabled switches.
6. Exogenous data provenance, random seed, source and input manifest hashes, and native results/evidence ZIP hash.
7. AC convergence, voltage criteria, action-readback consistency, topology assumptions and any available load-service/thermal measurements.

## Interpretation and redistribution caveats

- RBC selected-route continuation is **not** a freshly optimized electrical RBC route at each step.
- Connected-load estimates and their integrated energy proxies are not directly measured AC-delivered kW/kWh.
- Voltage-only AC checks do not certify conductor ampacity, phase-specific security or safe field switching.
- Bundled one-line diagram bus coordinates are not latitude/longitude.
- The project license has **not** been selected. Original example-feeder rights and archived path/privacy records require review before public GitHub visibility.
