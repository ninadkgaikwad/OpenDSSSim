import json
from pathlib import Path

from opendsssim.environment.simulator import OpenDSSSimulator
from opendsssim.persistence.manifest import compute_source_identity, write_runtime_manifest


FIXTURE = Path(__file__).parents[2] / "fixtures" / "a01_minimal" / "Master.dss"


def test_source_identity_is_deterministic(tmp_path):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    first = compute_source_identity(tmp_path)
    second = compute_source_identity(tmp_path)
    assert first == second
    assert len(first) == 64


def test_runtime_manifest_written_atomically(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "x.txt").write_text("x", encoding="utf-8")

    env = OpenDSSSimulator(FIXTURE)
    try:
        _, info = env.reset()
        output = tmp_path / "manifest.json"
        manifest = write_runtime_manifest(
            output,
            repo_root=repo,
            engine_version=info["solution"]["engine_version"],
            context_identity=env.context_identity,
        )
        payload = json.loads(output.read_text(encoding="utf-8"))
        assert payload["patch_id"] == manifest.patch_id
        assert payload["current_source_identity_sha256"]
    finally:
        env.close()
