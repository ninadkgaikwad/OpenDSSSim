"""A05I3 physical replay on both frozen IEEE-123 feeder variants."""
import csv
from pathlib import Path
import pytest
from opendsssim.environment import OpenDSSSimulator, ReplaySource, ReplayBinding, ReplaySpec
from opendsssim.runtime.access import SemanticRuntimeAccess
from opendsssim.semantics.schema import NativePropertyAddress

FEEDERS = Path(__file__).resolve().parents[2] / "experiments" / "pesgm2027" / "feeders"


def _csv(path):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(("time", "load_kw", "load_kvar"))
        w.writerows((("2026-01-01T00:00:00Z",32,11),
                     ("2026-01-01T01:00:00Z",25,-5)))
    return path


def _read(env, prop):
    return float(SemanticRuntimeAccess(env._plant.backend).read(NativePropertyAddress("Load.S1a", prop)))


@pytest.mark.parametrize("feeder", ["ieee123_base", "ieee123_pesgm2027"])
@pytest.mark.parametrize("mode", ["strict", "tile"])
def test_native_true_snapshot_replay_and_provenance(tmp_path, feeder, mode):
    p = _csv(tmp_path / "real.csv")
    replay = ReplaySpec((ReplaySource("file-a", "time", "UTC", p),),
                        (ReplayBinding("file-a", "load", ("Load.S1a",), "absolute_pq",
                                       ("load_kw", "load_kvar"), ("kW", "kvar")),),
                        mode=mode, max_steps=5)
    env = OpenDSSSimulator(FEEDERS / feeder / "IEEE123Master.dss", exogenous_replay=replay,
                           inventory_dir=tmp_path / "inv", semantic_registry_dir=tmp_path / "sem")
    try:
        original = env._plant.backend.solve_snapshot
        solves = [0]
        def counted():
            solves[0] += 1
            return original()
        env._plant.backend.solve_snapshot = counted
        _, reset = env.reset()
        assert solves[0] == 1 and reset["solution"]["converged"]
        assert reset["time"]["dt_seconds"] == 3600
        assert _read(env, "kW") == pytest.approx(32)
        _, _, _, truncated, first = env.step({})
        assert solves[0] == 2 and not truncated
        assert _read(env, "kW") == pytest.approx(32)
        assert first["time"]["electrical_sample_time_utc"] == reset["time"]["electrical_sample_time_utc"]
        _, _, _, truncated, second = env.step({})
        assert solves[0] == 3 and _read(env, "kW") == pytest.approx(25)
        assert truncated == (mode == "strict")
        assert second["exogenous"]["replay"]["sources"][0]["canonical_index"] == 1
        if mode == "tile":
            _, _, _, t3, third = env.step({})
            assert not t3 and _read(env, "kW") == pytest.approx(32)
            assert solves[0] == 4
            assert third["exogenous"]["replay"]["sources"][0]["replay_cycle"] == 1
            env.step({}); _, _, _, last, fifth = env.step({})
            assert last and solves[0] == 6
        else:
            assert second["time"]["truncation_reason"] == "data_exhausted"
            with pytest.raises(RuntimeError, match="reset"):
                env.step({})
    finally:
        env.close()
