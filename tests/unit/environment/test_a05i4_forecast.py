"""A05I4 source-derived oracle: no Plant/AltDSS interactions."""
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from hashlib import sha256
import pytest

from opendsssim.environment import (
    ExogenousForecastOracle, ForecastCoverageError, ForecastError,
    ForecastSelectionError, ForecastUnavailableError,
    EpisodeClock, EpisodeSpec, ExogenousProfileSpec, LoadSeries, PVSeries,
    ReplayTable, ReplaySource, ReplayBinding, ReplaySpec, ReplaySession,
)


def _session(*, mode="tile", interleaved=False):
    times=("2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z", "2026-01-01T02:00:00Z")
    tab=ReplayTable(times, {"p": (10,20,30), "q": (1,2,3)}, sha256(b"load").hexdigest())
    b=ReplayBinding("L", "load", ("Load.S1a",), "absolute_pq", ("p","q"), ("kW","kvar"))
    sources=(ReplaySource("L", "time", "UTC", table=tab),)
    bindings=(b,)
    if interleaved:
        pv=ReplayTable(times, {"irr": (.5,.6,.7)}, sha256(b"pv").hexdigest().upper())
        sources=(ReplaySource("V", "time", "UTC", table=pv),)+sources
        bindings=(ReplayBinding("V", "pv", ("PVSystem.PVD47",), "irradiance", ("irr",), ("kW/m2",)),)+bindings
    spec=ReplaySpec(sources,bindings,mode=mode,max_steps=7)
    session=ReplaySession(spec)
    clock=EpisodeClock(session.episode_spec,"episode-000001",123)
    return ExogenousForecastOracle(clock=clock,replay_session=session,replay_spec=spec,explicit_source=None)


def _get(result, lead, channel, entity="Load.S1a"):
    return next(v for v in result.values if (v.lead_index,v.channel_id,v.entity_id)==(lead,channel,entity))


def test_same_source_tile_cycle_and_decision_anchor_not_electrical_timestamp():
    oracle=_session()
    a=oracle.request(0,4,channel_ids=("load.kw",))
    assert [v.value for v in a.values]==[10,20,30,10]
    assert [v.replay_cycle for v in a.values]==[0,0,0,1]
    assert a.values[3].source_timestamp_utc=="2026-01-01T00:00:00+00:00"
    b=oracle.request(1,2)
    assert _get(b,0,"load.kw").value==20
    assert b.issue_time_utc=="2026-01-01T01:00:00+00:00"
    assert _get(b,0,"load.kw").valid_interval_start_utc==b.issue_time_utc
    assert oracle.request(0,4,channel_ids=("load.kw",))==a


def test_strict_future_coverage_does_not_mutate_source_or_clock():
    oracle=_session(mode="strict")
    assert _get(oracle.request(2,1),0,"load.kw").value==30
    with pytest.raises(ForecastCoverageError,match="COVERAGE"):
        oracle.request(2,2)
    assert _get(oracle.request(0,1),0,"load.kw").value==10


def test_interleaved_pv_and_load_provenance_are_not_swapped():
    r=_session(interleaved=True).request(0,1)
    pv=_get(r,0,"pv.irradiance","PVSystem.PVD47")
    ld=_get(r,0,"load.kw")
    assert pv.source_sha256==sha256(b"pv").hexdigest().upper()
    assert ld.source_sha256==sha256(b"load").hexdigest().upper()
    assert _get(r,0,"pv.cell_temperature","PVSystem.PVD47").value==25.0


def test_channel_entity_selection_fail_closed_and_no_source():
    oracle=_session()
    with pytest.raises(ForecastSelectionError):oracle.request(0,1,channel_ids=("voltage",))
    with pytest.raises(ForecastSelectionError):oracle.request(0,1,entity_ids=("Load.invalid",))
    with pytest.raises(ForecastError):oracle.request(0,0)
    with pytest.raises(ForecastError):oracle.request(0,True)
    with pytest.raises(ForecastSelectionError):oracle.request(0,1,channel_ids="load.kw")
    clock=EpisodeClock(EpisodeSpec(),"none",None)
    empty=ExogenousForecastOracle(clock=clock,replay_session=None,replay_spec=None,explicit_source=None)
    with pytest.raises(ForecastUnavailableError):empty.request(0,1)
    assert empty.request(0,1,required=False).status=="NOT_CONFIGURED"


def test_explicit_p_signed_pf_and_faiman_physical_parity():
    explicit=ExogenousProfileSpec("original",(
        LoadSeries(("Load.S1a",),"p_signed_pf",((10.0,-0.8),(20.0,1.0))),
    ), (
        PVSeries(("PVSystem.PVD47",),(.8,.4),(20.,21.),(5.,4.)),
    ))
    clock=EpisodeClock(EpisodeSpec(datetime(2026,1,1,tzinfo=timezone.utc),3600),"e",2)
    oracle=ExogenousForecastOracle(clock=clock,replay_session=None,replay_spec=None,explicit_source=explicit)
    a=oracle.request(0,2)
    assert _get(a,0,"load.kvar").value==pytest.approx(-7.5)
    assert _get(a,1,"load.kvar").value==pytest.approx(0.)
    assert _get(a,0,"pv.cell_temperature","PVSystem.PVD47").value==pytest.approx(20+800/(25+6.84*5))
    assert a.values[0].source_sha256==explicit.source_sha256
    with pytest.raises(ForecastCoverageError):oracle.request(1,2)
    with pytest.raises((FrozenInstanceError, AttributeError)):
        a.values[0].value=90
    detached=a.to_dict();detached["values"][0]["value"]=-999
    assert a.values[0].value!=-999


def test_csv_and_parquet_replay_forecast_parity_with_distinct_source_hashes(tmp_path):
    import csv
    import pyarrow as pa
    import pyarrow.parquet as pq
    lines=[("2026-01-01T00:00:00Z",8,2),("2026-01-01T01:00:00Z",12,4)]
    csvfile=tmp_path/"truth.csv"
    with csvfile.open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f);w.writerow(("time","p","q"));w.writerows(lines)
    parquet=tmp_path/"truth.parquet"
    pq.write_table(pa.table({"time":[x[0] for x in lines],"p":[x[1] for x in lines],"q":[x[2] for x in lines]}),parquet)
    records=[]
    for p in (csvfile,parquet):
        spec=ReplaySpec((ReplaySource("data","time","UTC",p),),
            (ReplayBinding("data","load",("Load.S1a",),"absolute_pq",("p","q"),("kW","kvar")),),mode="tile")
        session=ReplaySession(spec)
        oracle=ExogenousForecastOracle(clock=EpisodeClock(session.episode_spec,"episode",None),
            replay_session=session,replay_spec=spec,explicit_source=None)
        result=oracle.request(0,3,channel_ids=("load.kw",))
        records.append(result)
        assert [x.value for x in result.values]==[8,12,8]
        assert result.values[0].source_sha256==sha256(p.read_bytes()).hexdigest().upper()
    assert records[0].values[0].source_sha256 != records[1].values[0].source_sha256


def test_replay_signed_pf_matches_qualified_physical_equation():
    tab=ReplayTable(("2026-01-01T00:00:00Z","2026-01-01T01:00:00Z"),
                    {"p":(10,20),"pf":(-.8,1.0)},sha256(b"pf").hexdigest())
    binding=ReplayBinding("p","load",("Load.S1a",),"p_signed_pf",("p","pf"),("kW","signed_pf"))
    spec=ReplaySpec((ReplaySource("p","time","UTC",table=tab),),(binding,),mode="strict")
    session=ReplaySession(spec)
    oracle=ExogenousForecastOracle(clock=EpisodeClock(session.episode_spec,"e",None),
                                   replay_session=session,replay_spec=spec,explicit_source=None)
    record=oracle.request(0,2)
    assert _get(record,0,"load.kvar").value==pytest.approx(-7.5)
    assert _get(record,1,"load.kvar").value==pytest.approx(0)
