# OpenDSSSim_ControllerScience_C0A_DocumentationScaffold_v01R3_20261005

**Status:** documentation-only controller-science scaffold, reconciliation revision  
**Date:** 2026-10-05

## Purpose

Complete C0A safely after the initial R1 partial installation and reconcile the legitimate
pre-existing `docs/development/control_science/README.md` with the newer controller-science
repository organization.

## Known README provenance accepted by R3

R3 may replace `docs/development/control_science/README.md` only when its current SHA256 is
one of these explicitly audited values:

- pre-existing repository README:
  `D81C29539655B1CFA26D55E5771D0E1917847CE37646DEFE37A87DA8973C8442`
- R1 payload README:
  `D9D8BC2C62B9C6A2C778368B241927F2FEF38C68B178FDC6A41E2CA0812D5A56`
- R2 payload README:
  `F65D7E7DBE6A4E4B927D51FB48D9E69B5C945917DE1C050D11EBC6893D3A9ACE`

Any other README content causes a hard stop.

## Merge policy

The R3 README preserves the earlier repository document's:
- ownership boundary;
- status vocabulary;
- 17-field per-controller freeze record;
- fair-comparison rule;
- implementation gate;
- synchronization points;
- architecture-reference linkage.

It adds the newer scaffold's:
- reusable-vs-paper-specific repository ownership;
- generalized-controller and explicit unsupported semantics;
- RL feeder-universality nuance;
- C0-C6 development sequence;
- detailed directory map;
- requested/applied/realized action boundary.

## Runtime preservation

R3 modifies no files under:
- `src/`;
- `tests/`;
- `pyproject.toml`.

Previously installed byte-identical C0A scaffold files are skipped.
Missing C0A files are installed.
Unexpected divergent files cause a hard failure.
