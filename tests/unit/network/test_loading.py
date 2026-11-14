from pathlib import Path

import pytest

from opendsssim.network.loading import CircuitSource


FIXTURE = Path(__file__).parents[2] / "fixtures" / "a01_minimal" / "Master.dss"


def test_circuit_source_hash_and_validation():
    source = CircuitSource.from_path(FIXTURE)
    assert source.master_path == FIXTURE.resolve()
    assert len(source.sha256) == 64
    source.validate()


def test_circuit_source_rejects_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        CircuitSource.from_path(tmp_path / "missing.dss")
