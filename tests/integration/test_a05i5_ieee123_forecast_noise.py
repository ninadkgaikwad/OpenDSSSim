"""A05I5 genuine AltDSS: forecast perturbations never touch physical truth."""
from pathlib import Path
import csv
import pytest

from opendsssim.environment import (
    OpenDSSSimulator, ReplaySource, ReplayBinding, ReplaySpec,
    ForecastNoiseSpec, GaussianScale, ForecastCoverageError,
)
from opendsssim.runtime.access import SemanticRuntimeAccess
from opendsssim.semantics.schema import NativePropertyAddress

FEEDERS=Path(__file__).resolve().parents[2]/"experiments"/"pesgm2027"/"feeders"


@pytest.mark.parametrize("feeder",["ieee123_base","ieee123_pesgm2027"])
@pytest.mark.parametrize("mode",["tile","strict"])
def test_a05i5_native_seeded_forecast_preserves_snapshot_truth(tmp_path,feeder,mode):
    path=tmp_path/"loads.csv"
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.writer(f);w.writerow(("time","p","q"))
        w.writerows((("2026-01-01T00:00:00Z",32,11),
                     ("2026-01-01T01:00:00Z",25,-5)))
    replay=ReplaySpec((ReplaySource("L","time","UTC",path),),
        (ReplayBinding("L","load",("Load.S1a",),"absolute_pq",("p","q"),("kW","kvar")),),
        mode=mode,max_steps=4)
    noise=ForecastNoiseSpec("additive_gaussian",seed=814,boundary="truncate",scales=(
        GaussianScale("load.kw","Load.S1a",sigma=3),
        GaussianScale("load.kvar","Load.S1a",sigma=2),))
    env=OpenDSSSimulator(FEEDERS/feeder/"IEEE123Master.dss",
        exogenous_replay=replay,forecast_noise=noise,
        inventory_dir=tmp_path/"inventory",semantic_registry_dir=tmp_path/"semantic")
    try:
        backend=env._plant.backend
        original=backend.solve_snapshot; solves=[0]
        def counted():
            solves[0]+=1
            return original()
        backend.solve_snapshot=counted
        _,info=env.reset(seed=501)
        assert info["solution"]["converged"] and solves[0]==1
        access=SemanticRuntimeAccess(backend)
        def physical():return float(access.read(NativePropertyAddress("Load.S1a","kW")))
        assert physical()==pytest.approx(32)
        original_write=backend.write_object_property
        def no_native_write(*args,**kwargs):raise AssertionError("A05I5 forecast wrote native data")
        backend.write_object_property=no_native_write
        try:
            a=env.exogenous_forecast(2)
            b=env.exogenous_forecast(2)
            assert a==b and a.forecast_mode=="synthetic_additive_gaussian"
            assert len(a.values)==4
            assert a.values[0].noise_sigma is not None
            assert env.exogenous_forecast(1,channel_ids=("load.kw",)).values[0].value == next(
                v.value for v in a.values if v.lead_index==0 and v.channel_id=="load.kw")
            assert solves[0]==1 and physical()==pytest.approx(32)
            if mode=="strict":
                with pytest.raises(ForecastCoverageError):env.exogenous_forecast(3)
        finally:
            backend.write_object_property=original_write
        assert all("unperturbed" not in str(k).lower() for k in a.to_dict())
        _,_,_,trunc,step=env.step({})
        assert not trunc and solves[0]==2 and physical()==pytest.approx(32)
        rolled=env.exogenous_forecast(1)
        assert rolled.issue_time_utc==step["time"]["decision_time_utc"]
        assert rolled.issue_time_utc!=step["time"]["electrical_sample_time_utc"]
        assert solves[0]==2
        _,_,_,_,_=env.step({})
        assert solves[0]==3 and physical()==pytest.approx(25)
    finally:
        env.close()


def test_a05i5_working_feeder_weather_pv_truth_unchanged(tmp_path):
    from opendsssim.environment import ExogenousProfileSpec, PVSeries, EpisodeSpec
    source=ExogenousProfileSpec("faiman-native",pvs=(
        PVSeries(("PVSystem.PVD47",),(.8,.6),(20,22),(5,2)),
        PVSeries(("PVSystem.PVD76",),(.7,.5)),
    ))
    scales=(
        GaussianScale("pv.irradiance","PVSystem.PVD47",sigma=.2),
        GaussianScale("pv.outdoor_temperature","PVSystem.PVD47",sigma=2),
        GaussianScale("pv.wind_speed","PVSystem.PVD47",sigma=1),
        GaussianScale("pv.irradiance","PVSystem.PVD76",sigma=.1),
    )
    env=OpenDSSSimulator(FEEDERS/"ieee123_pesgm2027"/"IEEE123Master.dss",
        exogenous=source,episode_spec=EpisodeSpec(max_steps=2),
        forecast_noise=ForecastNoiseSpec("additive_gaussian",99,scales=scales),
        inventory_dir=tmp_path/"inv",semantic_registry_dir=tmp_path/"sem")
    try:
        env.reset(seed=51)
        access=SemanticRuntimeAccess(env._plant.backend)
        def native(n,p):return float(access.read(NativePropertyAddress(n,p)))
        assert native("PVSystem.PVD47","Irradiance")==pytest.approx(.8)
        assert native("PVSystem.PVD76","Temperature")==pytest.approx(25)
        original=env._plant.backend.solve_snapshot; solves=[0]
        def counted():
            solves[0]+=1
            return original()
        env._plant.backend.solve_snapshot=counted
        forecast=env.exogenous_forecast(2)
        vals={(x.lead_index,x.entity_id,x.channel_id):x.value for x in forecast.values}
        g=vals[(0,"PVSystem.PVD47","pv.irradiance")]
        ta=vals[(0,"PVSystem.PVD47","pv.outdoor_temperature")]
        w=vals[(0,"PVSystem.PVD47","pv.wind_speed")]
        t=vals[(0,"PVSystem.PVD47","pv.cell_temperature")]
        assert t==pytest.approx(ta+1000*g/(25+6.84*w))
        assert vals[(0,"PVSystem.PVD76","pv.cell_temperature")]==25.0
        assert solves[0]==0
        assert native("PVSystem.PVD47","Irradiance")==pytest.approx(.8)
        assert native("PVSystem.PVD76","Temperature")==pytest.approx(25)
        assert forecast==env.exogenous_forecast(2)
        assert solves[0]==0
    finally:
        env.close()
