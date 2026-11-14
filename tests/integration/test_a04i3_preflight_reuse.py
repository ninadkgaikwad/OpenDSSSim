from __future__ import annotations

from pathlib import Path

from opendsssim.environment.simulator import OpenDSSSimulator
from opendsssim.problem import ObservationSpec, ProblemSpec, RegistryKind, SelectionGroup, SemanticQuery

FIXTURE = Path(__file__).parents[1] / "fixtures" / "a03_semantic" / "Master.dss"


def problem():
    return ProblemSpec.create(
        "a04i3-preflight", "1",
        observations=ObservationSpec(groups=(SelectionGroup("obs", (SemanticQuery(RegistryKind.STATE, quantity="solution_converged"),)),)),
    )


def test_a04i3_preflight_reused_for_identical_runtime_boundary(tmp_path: Path):
    kwargs = dict(inventory_dir=tmp_path/"inv", semantic_registry_dir=tmp_path/"sem", preflight_dir=tmp_path/"pre")
    env1 = OpenDSSSimulator(FIXTURE, problem=problem(), **kwargs)
    try:
        assert env1.preflight_status == "BUILT"
        first_path = env1.preflight_path
        env1.reset()
    finally:
        env1.close()
    env2 = OpenDSSSimulator(FIXTURE, problem=problem(), **kwargs)
    try:
        assert env2.preflight_status == "REUSED"
        assert env2.preflight_path == first_path
    finally:
        env2.close()
