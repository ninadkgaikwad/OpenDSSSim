# Tutorial 5 — Testing and reproducibility

## Test pyramid

**Level 0, offline, no AltDSS:** Python compile/static test; SHA-256 verification for every example input; pre-qualified static case checks; output overwrite rejection; reference plotting. These gates were exercised during packaging.

```powershell
python -m compileall -q src experiments examples/ieee123_course
python -m unittest discover -s examples/ieee123_course/tests -v
python examples/ieee123_course/run_course.py --lesson 00 --run-id integrity_001
python examples/ieee123_course/run_course.py --lesson 10 --run-id figures_001
```

**Level 1, native no Gurobi:** install base project and run Lessons 01–06 and 08, using an environment with a working AltDSS runtime. Check convergence, Gym space membership, physical action audits and immutable input hashes.

**Level 2, licensed optimization:** with valid Gurobi installation, run Lessons 07 and 09; verify model statuses, original `p2_milp.py` hash, native AC steps, action feedback, input and source integrity. Changing objective priorities is a separate scientific sensitivity.

**Level 3, extended research:** run six 24-step experiments with `--paper-campaign --steps 24`, then audit all outputs and compare against qualified archived data by objective, topology, voltage, and service proxy. This build does **not** claim that these six newly authored tutorial lessons have already been native qualified.

## Native smoke sequence on a clean clone

```powershell
python -m pip install -e ".[dev]"
python -m pip install -r examples/ieee123_course/requirements-tutorial.txt
python examples/ieee123_course/run_course.py --lesson 01 --run-id smoke_snapshot
python examples/ieee123_course/run_course.py --lesson 02 --run-id smoke_problem
python examples/ieee123_course/run_course.py --lesson 03 --steps 2 --run-id smoke_clock
python examples/ieee123_course/run_course.py --lesson 05 --run-id smoke_context
```

Do **not** interpret success of the offline Level-0 tests as proof that the native AltDSS, Gurobi, RBC or MPC experiments work in every operating system. Native tests are environmental and may require adjustment after examining real receipts.

## Reproducibility controls

Every runner checks input SHA-256 before creating output, refuses to overwrite a prior run ID, catches errors, preserves a partial receipt, and closes its native simulator context in a `finally` block. `input/` data are read-only by convention and are covered by a source manifest; the original `src/opendsssim/` is protected by source-preservation audit.

The output may contain path strings specific to the machine. Review it before posting receipts online. Record Python, AltDSS and (if used) Gurobi versions for publication-level reproducibility. Keep scientific control parameters consistent across experiments unless a sensitivity is deliberately labeled.

## Dependency matrix

| Lesson | NumPy | AltDSS + Gymnasium | Matplotlib | Gurobi |
|---|---|---|---|---|
| 00 / integrity | Yes | No | No | No |
| 01–06, 08 | Yes | Yes | No | No |
| 07 / 09 | Yes | Yes | No | Yes |
| 10 / plot | Yes | No | Yes | No |

## Why the course does not run a private backend from its scripts

Native mutation in controller code bypasses action authority, fault locks, semantic shape/bounds checking and output audit trails. The public `ControllerContext` and `env.step` are the protected integration surface. Any improvements to the simulator must be controller-agnostic and separately reviewed.
