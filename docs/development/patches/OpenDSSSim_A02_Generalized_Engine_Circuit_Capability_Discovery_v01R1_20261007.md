# OpenDSSSim_A02_Generalized_Engine_Circuit_Capability_Discovery_v01R1_20261007

## Patch identity

- Date: 2026-10-07
- Stage: A02
- PRE-A02 source-manifest SHA256: `8D6A5D3548B90A515C38710B66ED6D814EE28E27C47E9D97FEAA680B7EE966A8`
- Directed input SHA256: `822ED62F6A3A57C3CEBEC40DD982E9CCEAF60FFB99EA02A15111D80387DB696A`
- Environment: `scalebridge-dev-gpu-laptop`
- Environment mutation: **NONE**

## Purpose

Implement deterministic, read-only generalized AltDSS engine and circuit
discovery while preserving the A01 physical plant lifecycle.

## Frozen contract

See:

`docs/development/architecture/OpenDSSSim_A02_Generalized_Engine_Circuit_Capability_Discovery_Contract_v01_20261006.md`

## Input discipline

The patch is installable only against the exact 62-file PRE-A02 repository
snapshot. This includes controller-science C0A documentation already present in
the shared Dropbox repository.

Any parallel-track drift causes installer refusal rather than merging against a
mixed predecessor.

## Files changed

Modified predecessor files:

```text
scripts/validation/validate_a01.py
src/opendsssim/__init__.py
src/opendsssim/backends/base.py
src/opendsssim/backends/altdss_backend.py
src/opendsssim/environment/simulator.py
src/opendsssim/plant/core.py
```

New files:

```text
docs/development/architecture/OpenDSSSim_A02_Generalized_Engine_Circuit_Capability_Discovery_Contract_v01_20261006.md
docs/development/patches/OpenDSSSim_A02_Generalized_Engine_Circuit_Capability_Discovery_v01R1_20261007.md
scripts/validation/validate_a02.py
src/opendsssim/discovery/__init__.py
src/opendsssim/discovery/schema.py
tests/integration/test_a02_discovery.py
tests/unit/backends/test_a02_discovery.py
tests/unit/discovery/test_schema.py
```

## A01 validator adaptation

The A01 standalone validator now checks the frozen
`A01_FOUNDATION_PATCH_ID` rather than requiring the repository's current
`PATCH_ID` to remain A01 forever.

The A01 behavioral gates remain active.

## Non-goals

A02 does not implement registries, mutability classification, ProblemSpec,
generalized Gym spaces, external time series, action realization, controllers,
optimization, RL, Gurobi, or the IEEE-123 production experiment.

## Rollback

The installer backs up each modified predecessor file before copying payload.
On failure it restores modified files and removes newly created files/directories.

## Successor

A03 — generalized seven-registry construction and semantic classification.

## Revision note

This `v01R1` supersedes the failed `v01` installation attempt.

The `v01` implementation itself passed:

- A01 standalone regression;
- A02 standalone discovery validation.

The installer then failed during full pytest collection because two newly added
test files shared the basename `test_a02_discovery.py` in different directories.
With the repository's current non-package test layout, pytest imported the
integration module first and rejected the unit module as an import-file mismatch.

The installer rolled back the A02 payload after that failure.

`v01R1` changes no A02 science, discovery schema, backend logic, plant logic,
or validation semantics. It only gives the two tests unique module basenames:

```text
tests/integration/test_a02_discovery_integration.py
tests/unit/backends/test_a02_backend_discovery.py
```

The default pytest import mode is intentionally retained. This fixes the test
layout instead of masking the collision with a special pytest option.
