from pathlib import Path
import shutil
from unittest.mock import patch

from opendsssim.backends.altdss_backend import AltDSSBackend
from opendsssim.environment.simulator import OpenDSSSimulator


FIXTURE = Path(__file__).parents[1] / "fixtures" / "a01_minimal" / "Master.dss"


def test_inventory_is_built_once_then_reused_without_rediscovery(tmp_path):
    circuit_dir = tmp_path / "circuit"
    circuit_dir.mkdir()
    master = circuit_dir / "Master.dss"
    shutil.copy2(FIXTURE, master)
    cache = tmp_path / "inventory"

    env_a = OpenDSSSimulator(master, inventory_dir=cache)
    try:
        assert env_a.inventory_status == "MISSING"
        env_a.reset(seed=1)
        assert env_a.inventory_status == "BUILT"
        assert env_a.inventory_build_count == 1
        assert env_a.inventory_path.exists()
        first_hash = env_a.circuit_inventory.semantic_sha256

        with patch.object(
            AltDSSBackend,
            "discover_circuit",
            side_effect=AssertionError("inventory rediscovery is forbidden"),
        ):
            env_a.reset(seed=2)

        assert env_a.inventory_status == "REUSED"
        assert env_a.inventory_build_count == 1
    finally:
        env_a.close()

    env_b = OpenDSSSimulator(master, inventory_dir=cache)
    try:
        assert env_b.inventory_status == "LOADED"

        with patch.object(
            AltDSSBackend,
            "discover_circuit",
            side_effect=AssertionError("cached inventory must avoid rediscovery"),
        ):
            env_b.reset(seed=3)

        assert env_b.inventory_status == "REUSED"
        assert env_b.inventory_build_count == 0
        assert env_b.circuit_inventory.semantic_sha256 == first_hash
    finally:
        env_b.close()


def test_source_change_invalidates_cache_key(tmp_path):
    circuit_dir = tmp_path / "circuit"
    circuit_dir.mkdir()
    master = circuit_dir / "Master.dss"
    dependency = circuit_dir / "Data.csv"
    shutil.copy2(FIXTURE, master)
    dependency.write_text("1\n", encoding="utf-8")
    cache = tmp_path / "inventory"

    env_a = OpenDSSSimulator(master, inventory_dir=cache)
    try:
        env_a.reset()
        old_path = env_a.inventory_path
    finally:
        env_a.close()

    dependency.write_text("2\n", encoding="utf-8")

    env_b = OpenDSSSimulator(master, inventory_dir=cache)
    try:
        assert env_b.inventory_status == "MISSING"
        assert env_b.inventory_path != old_path
        env_b.reset()
        assert env_b.inventory_status == "BUILT"
    finally:
        env_b.close()
