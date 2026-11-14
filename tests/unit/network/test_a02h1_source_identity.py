from pathlib import Path
import shutil

from opendsssim.network.loading import CircuitSource


FIXTURE_DIR = Path(__file__).parents[2] / "fixtures" / "a02h1_control"


def test_source_tree_identity_covers_nested_dependencies(tmp_path):
    target = tmp_path / "circuit"
    shutil.copytree(FIXTURE_DIR, target)

    source_a = CircuitSource.from_path(target / "Master.dss")
    assert source_a.dependency_count == 3
    assert len(source_a.source_tree_sha256) == 64

    controls = target / "Controls.dss"
    controls.write_text(
        controls.read_text(encoding="utf-8") + "\n! identity change\n",
        encoding="utf-8",
    )

    source_b = CircuitSource.from_path(target / "Master.dss")
    assert source_b.sha256 == source_a.sha256
    assert source_b.source_tree_sha256 != source_a.source_tree_sha256


def test_source_root_can_be_explicitly_broadened(tmp_path):
    root = tmp_path / "root"
    circuit = root / "case"
    circuit.mkdir(parents=True)
    master = circuit / "Master.dss"
    master.write_text("Clear\nNew Circuit.X basekv=12.47 bus1=s\n", encoding="utf-8")
    (root / "external.csv").write_text("1,2,3\n", encoding="utf-8")

    source = CircuitSource.from_path(master, source_root=root)
    paths = {item.relative_path for item in source.dependencies}
    assert "case/Master.dss" in paths
    assert "external.csv" in paths
