from __future__ import annotations

from pathlib import Path

from opendsssim.persistence.preflight import A04RuntimePreflightRecord, _opendsssim_version, ensure_preflight


def _record(binding="A" * 64):
    return A04RuntimePreflightRecord(
        schema_version="A04.runtime-preflight.v1", status="PASS",
        implementation_source_sha256="B" * 64, backend="altdss", altdss_version="0.2.4", engine_version="e",
        python_version="3.10", gymnasium_version="1.2.3", opendsssim_version="0.1.0a6",
        inventory_semantic_sha256="C" * 64, semantic_bundle_sha256="D" * 64,
        resolved_problem_sha256="E" * 64, observation_space_sha256="F" * 64,
        action_space_sha256="1" * 64, gym_space_contract_sha256="2" * 64,
        runtime_binding_sha256=binding, hook_identities=("r", "t", "x"),
    )


def test_a04i3_preflight_build_reuse_and_invalidation(tmp_path: Path):
    first = _record()
    status1, path1 = ensure_preflight(first, tmp_path)
    status2, path2 = ensure_preflight(first, tmp_path)
    changed = _record("9" * 64)
    status3, path3 = ensure_preflight(changed, tmp_path)
    assert status1 == "BUILT"
    assert status2 == "REUSED"
    assert path1 == path2
    assert status3 == "BUILT"
    assert path3 != path1


def test_a04i3_source_layout_reports_package_version_without_install():
    assert _opendsssim_version() == "0.1.0a6"
