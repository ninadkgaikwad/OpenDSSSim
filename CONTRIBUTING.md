# Contributing to OpenDSSSim

We welcome reproducible issue reports and carefully scoped improvements after the repository's license and publication permissions are resolved.

1. Open an issue describing the affected public API, circuit variant, ProblemSpec, expected behavior, and precise source versions.
2. Include a minimal reproducible example using only `env.controller_context()`, the public action layout, and `env.step()`—never bypass the simulator with backend mutation.
3. Separate **controller-side** changes from genuine **controller-agnostic simulator** changes. The frozen physical backend, registries and Plant must not be changed to accommodate a single policy.
4. For any implementation repair, collect a fresh, read-only full repository tree and tree-derived directed-source evidence first; attach auditable hashes and an independent qualification result.
5. Provide tests, documentation, an exact release manifest, and scientific limitations. Do not claim AC, thermal, radiality or energy outcomes not present in native evidence.
6. Never commit credentials, local personal paths, or unapproved redistribution of third-party datasets.

Run `python -m unittest discover -s examples/ieee123_course/tests -v` for quick portable example checks, then native/Gurobi experiments as required by the affected capability. See `docs/tutorial/05_TESTING_AND_REPRODUCIBILITY.md`.
