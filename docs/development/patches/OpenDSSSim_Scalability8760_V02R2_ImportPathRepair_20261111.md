# OpenDSSSim Scalability8760 V02R2 Import-Path Repair

## Scope

Minimal source-only repair after the V02R1 package-construction failure.

The original V02 science remains unchanged.

## Evidence

Fresh post-rollback tree SHA256:

`E27C8D82903237DA3D030E2B26FD54B02E6B42978031BD89D30850187F89666A`

Tree-derived V02R2 directed evidence SHA256:

`7FB29A49694E99CE3B07053B7A0E171E7609B5DC86BBF5244EC0F7E868D7107A`

Directed verification:

- selected files: 41
- verified files: 41
- transient cache paths selected: 0
- scientific runner executed: NO
- repository modified: NO

## Root cause

The OpenDSSSim repository uses a setuptools `src/` layout. Directly launching the
experiment with `python <script>` did not place `<RepoRoot>/src` on `sys.path`.

Read-only evidence showed:

- plain `find_spec("opendsssim")` -> `None`
- prepending `<RepoRoot>/src` resolved `src/opendsssim/__init__.py`

OpenDSSSim's existing standalone validation scripts use the same repository-local
`src` bootstrap pattern.

## Repair

Exactly one executable source file is replaced:

`experiments\pesgm2027\scalability_8760_external_pq\run_external_pq_native_h3.py`

The runner derives its repository root from `__file__`, prepends `<RepoRoot>/src`
to `sys.path`, and then imports OpenDSSSim.

Preimage SHA256:

`6590303124CD375C6C4C1BE4E7B1E8B604F22EFC8E300355050F5F4F4720F298`

Repaired SHA256:

`8EB3843232523EACEDFCA21308A238A6B54D19CF0711987E368783C5BFB5CE54`

## Explicit non-changes

- `src/opendsssim`: unchanged
- 8760 profile: unchanged
- profile SHA256: `2E4447CE612E1ECBFBC891F5A75F23F67AC7C11AF40E9FAAA75491CB5DC0BD2C`
- A05 replay semantics: unchanged
- native ProblemSpec/controller semantics: unchanged
- HistoryLevel.H3: unchanged
- Gaussian seed/sigma: unchanged
- feeder baselines: unchanged
- no `.pyc` or `__pycache__` packaged
