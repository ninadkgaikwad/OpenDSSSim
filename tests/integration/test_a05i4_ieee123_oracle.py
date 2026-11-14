"""True AltDSS snapshots and read-only A05I4 forecast parity, both feeders."""
from pathlib import Path
import csv
import pytest

from opendsssim.environment import OpenDSSSimulator, ReplaySource, ReplayBinding, ReplaySpec, ForecastCoverageError
from opendsssim.runtime.access import SemanticRuntimeAccess
from opendsssim.semantics.schema import NativePropertyAddress

FEEDERS=Path(__file__).resolve().parents[2]/"experiments"/"pesgm2027"/"feeders"


@pytest.mark.parametrize("feeder",["ieee123_base","ieee123_pesgm2027"])
@pytest.mark.parametrize("mode",["tile","strict"])
def test_a05i4_forecast_is_readonly_and_next_decision_anchored(tmp_path,feeder,mode):
    path=tmp_path/"load.csv"
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.writer(f);w.writerow(("time","p","q"))
        w.writerows((("2026-01-01T00:00:00Z",32,11),("2026-01-01T01:00:00Z",25,-5)))
    replay=ReplaySpec((ReplaySource("L","time","UTC",path),),
        (ReplayBinding("L","load",("Load.S1a",),"absolute_pq",("p","q"),("kW","kvar")),),
        mode=mode,max_steps=4)
    env=OpenDSSSimulator(FEEDERS/feeder/"IEEE123Master.dss",exogenous_replay=replay,
        inventory_dir=tmp_path/"inventory",semantic_registry_dir=tmp_path/"semantic")
    try:
        native=env._plant.backend
        original=native.solve_snapshot
        solves=[0]
        def counted():
            solves[0]+=1
            return original()
        native.solve_snapshot=counted
        obs,info=env.reset()
        baseline=float(SemanticRuntimeAccess(native).read(NativePropertyAddress("Load.S1a","kW")))
        assert baseline==pytest.approx(32)
        count=solves[0]
        original_write = native.write_object_property
        def forbid_write(*args, **kwargs):
            raise AssertionError("A05I4 forecast attempted a native write")
        native.write_object_property = forbid_write
        try:
            forecast=env.exogenous_forecast(2)
        finally:
            native.write_object_property = original_write
        assert solves[0]==count
        assert forecast.status=="AVAILABLE" and forecast.issue_time_utc==info["time"]["decision_time_utc"]
        assert [v.value for v in forecast.values if v.channel_id=="load.kw"]==[32,25]
        assert forecast.to_dict()==env.exogenous_forecast(2).to_dict()
        assert float(SemanticRuntimeAccess(native).read(NativePropertyAddress("Load.S1a","kW")))==baseline
        if mode=="strict":
            with pytest.raises(ForecastCoverageError):env.exogenous_forecast(3)
        _,_,_,truncated,step=env.step({})
        assert not truncated and solves[0]==count+1
        rolled=env.exogenous_forecast(1)
        assert rolled.issue_time_utc==step["time"]["decision_time_utc"]
        assert rolled.issue_time_utc!=step["time"]["electrical_sample_time_utc"]
        assert next(v.value for v in rolled.values if v.channel_id=="load.kw")==25
        assert solves[0]==count+1
    finally:
        env.close()
