"""A05I5 forecast-only error, seeded parity, domain and provenance contracts."""
from dataclasses import FrozenInstanceError
from hashlib import sha256
import math

import pytest

from opendsssim.environment import (
    EpisodeClock, EpisodeSpec, ExogenousForecastOracle, ExogenousProfileSpec,
    LoadSeries, PVSeries, ForecastNoiseEngine, ForecastNoiseSpec,
    ForecastNoiseError, ForecastNoiseCoverageError, GaussianScale,
    ReplayTable, ReplaySource, ReplayBinding, ReplaySpec, ReplaySession,
)


def _oracle(*, mode="tile", interleaved=False, episode="episode-001"):
    stamps=("2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z", "2026-01-01T02:00:00Z")
    table=ReplayTable(stamps,{"p":(10,20,30),"q":(1,2,3)},sha256(b"load").hexdigest())
    sources=(ReplaySource("L","time","UTC",table=table),)
    bindings=(ReplayBinding("L","load",("Load.S1a",),"absolute_pq",("p","q"),("kW","kvar")),)
    if interleaved:
        pv=ReplayTable(stamps,{"irr":(.5,.6,.7)},sha256(b"pv").hexdigest())
        sources=(ReplaySource("V","time","UTC",table=pv),)+sources
        bindings=(ReplayBinding("V","pv",("PVSystem.PVD47",),"irradiance",("irr",),("kW/m2",)),)+bindings
    spec=ReplaySpec(sources,bindings,mode=mode,max_steps=7)
    session=ReplaySession(spec)
    clock=EpisodeClock(session.episode_spec,episode,501)
    oracle=ExogenousForecastOracle(clock=clock,replay_session=session,replay_spec=spec,explicit_source=None)
    return oracle,spec,clock


def _scale(ch, ent="Load.S1a", sigma=1.0):
    return GaussianScale(ch,ent,sigma=sigma)


def _value(result, lead, name, ent="Load.S1a"):
    return next(x for x in result.values if x.lead_index==lead and x.channel_id==name and x.entity_id==ent)


def test_none_mode_is_exact_original_oracle_and_produces_no_audit():
    oracle, spec, clock=_oracle()
    original=oracle.request(0,3)
    engine=ForecastNoiseEngine(ForecastNoiseSpec(),replay_spec=spec,reset_seed=clock.reset_seed)
    assert engine.transform(original)==(original,())
    assert original.forecast_mode=="oracle_perfect_exogenous"


def test_seeded_stable_repeat_call_order_issue_identity_and_tiling():
    oracle,spec,clock=_oracle()
    settings=ForecastNoiseSpec(mode="additive_gaussian",seed=17,scales=(
        _scale("load.kw",sigma=3),_scale("load.kvar",sigma=2),))
    engine=ForecastNoiseEngine(settings,replay_spec=spec,reset_seed=clock.reset_seed)
    source=oracle.request(0,5)
    engine.validate_declared(source)
    a, audit=engine.transform(source)
    assert a==engine.transform(source)[0]
    engine.transform(oracle.request(1,2))  # unrelated issue cannot consume RNG
    assert a==engine.transform(source)[0]
    assert a.to_dict()==engine.transform(source)[0].to_dict()
    assert len(audit)==10
    assert _value(a,0,"load.kw").value!=_value(a,3,"load.kw").value
    assert _value(a,0,"load.kw").source_timestamp_utc==_value(a,3,"load.kw").source_timestamp_utc
    different_issue,_=engine.transform(oracle.request(1,1))
    assert _value(different_issue,0,"load.kw").value!=_value(a,1,"load.kw").value
    assert all(v.value>=0 for v in a.values if v.channel_id=="load.kw")
    assert a.forecast_mode=="synthetic_additive_gaussian"
    assert a.noise_config_sha256==settings.identity_sha256
    assert not any("raw_gaussian" in key or "unperturbed" in key for key in a.to_dict())
    assert all(x.source_sha256 for x in audit)


def test_selection_can_request_one_independent_primitive_with_one_sigma():
    oracle,spec,clock=_oracle(interleaved=True)
    settings=ForecastNoiseSpec("additive_gaussian",101,scales=(_scale("load.kw",sigma=4),))
    engine=ForecastNoiseEngine(settings,replay_spec=spec,reset_seed=clock.reset_seed)
    # The unselected load kvar/PV channels need not have configured sigmas.
    noisy,audit=engine.transform(oracle.request(0,2),channel_ids=("load.kw",),entity_ids=("Load.S1a",))
    assert len(noisy.values)==2 and len(audit)==2
    assert all(x.channel_id=="load.kw" for x in noisy.values)


def test_sigma_vector_linear_zero_and_required_lead_fail_closed():
    oracle,spec,clock=_oracle()
    original=oracle.request(0,3)
    assert GaussianScale("load.kw","Load.S1a",sigma0=1,alpha=2).at(3)==7
    assert GaussianScale("load.kw","Load.S1a",sigma=(0,2)).at(1)==2
    with pytest.raises(ForecastNoiseCoverageError):
        GaussianScale("load.kw","Load.S1a",sigma=(0,2)).at(2)
    zero=ForecastNoiseSpec("additive_gaussian",13,scales=(
        _scale("load.kw",sigma=0),_scale("load.kvar",sigma=0),))
    same,audit=ForecastNoiseEngine(zero,replay_spec=spec,reset_seed=clock.reset_seed).transform(original)
    assert [v.value for v in same.values]==[v.value for v in original.values]
    assert all(a.sigma==0 for a in audit)
    assert same.forecast_mode=="oracle_perfect_exogenous"
    missing=ForecastNoiseSpec("additive_gaussian",13,scales=(_scale("load.kw",sigma=(1,2)),))
    with pytest.raises(ForecastNoiseCoverageError):
        ForecastNoiseEngine(missing,replay_spec=spec).transform(original,channel_ids=("load.kw",))
    with pytest.raises(ForecastNoiseCoverageError):
        ForecastNoiseEngine(missing,replay_spec=spec).transform(original)


def test_gaussian_default_truncated_positive_and_explicit_clip_private_receipt():
    oracle,spec,clock=_oracle()
    truth=oracle.request(0,8)
    scales=(_scale("load.kw",sigma=100),_scale("load.kvar",sigma=100))
    trunc=ForecastNoiseEngine(ForecastNoiseSpec("additive_gaussian",777,scales=scales),
                             replay_spec=spec,reset_seed=clock.reset_seed)
    out, audit=trunc.transform(truth)
    assert all(v.value>=0 for v in out.values if v.channel_id=="load.kw")
    assert not any(v.was_clipped for v in out.values)
    assert not any(a.was_clipped for a in audit)
    clip=ForecastNoiseEngine(ForecastNoiseSpec("additive_gaussian",777,"clip",scales),
                            replay_spec=spec,reset_seed=clock.reset_seed)
    clipped, receipt=clip.transform(truth)
    assert len(receipt)==16
    assert any(a.was_clipped for a in receipt)
    assert any(a.raw_gaussian_value < 0 and a.accepted_value==0 for a in receipt
               if a.channel_id=="load.kw")
    assert all(v.value>=0 for v in clipped.values if v.channel_id=="load.kw")
    assert clipped.noise_mode=="additive_gaussian"
    assert not any("unperturbed_value" in item for item in clipped.to_dict()["values"])
    with pytest.raises((FrozenInstanceError,AttributeError)):
        receipt[0].accepted_value=1.0


def test_signed_pf_derived_q_uses_perturbed_p_and_pf():
    source=ExogenousProfileSpec("signed",loads=(LoadSeries(("Load.S1a",),"p_signed_pf",((10,-0.8),(12,-0.6))),))
    clock=EpisodeClock(EpisodeSpec(),"e",1)
    oracle=ExogenousForecastOracle(clock=clock,replay_session=None,replay_spec=None,explicit_source=source)
    settings=ForecastNoiseSpec("additive_gaussian",19,scales=(
        _scale("load.kw",sigma=2),_scale("load.signed_pf",sigma=.25),))
    engine=ForecastNoiseEngine(settings,explicit_source=source,reset_seed=clock.reset_seed)
    out,_=engine.transform(oracle.request(0,2))
    for lead in (0,1):
        p=_value(out,lead,"load.kw").value
        pf=_value(out,lead,"load.signed_pf").value
        q=_value(out,lead,"load.kvar").value
        assert p>=0 and -1<=pf<0
        assert q==pytest.approx(math.copysign(p*math.sqrt(max(0,1-pf*pf))/abs(pf),pf))
        assert _value(out,lead,"load.kvar").noise_sigma is None
    only_q,_=engine.transform(oracle.request(0,1),channel_ids=("load.kvar",))
    assert len(only_q.values)==1 and only_q.values[0].value==_value(out,0,"load.kvar").value


def test_pv_faiman_uses_noisy_primitives_and_fallback_is_25c():
    source=ExogenousProfileSpec("pv",pvs=(
        PVSeries(("PVSystem.PVD47",),(.7,.8),(20,21),(5,4)),
        PVSeries(("PVSystem.PVD76",),(.5,.4)),))
    clock=EpisodeClock(EpisodeSpec(),"e",100)
    oracle=ExogenousForecastOracle(clock=clock,replay_session=None,replay_spec=None,explicit_source=source)
    scales=(
        _scale("pv.irradiance","PVSystem.PVD47",.25),
        _scale("pv.outdoor_temperature","PVSystem.PVD47",2),
        _scale("pv.wind_speed","PVSystem.PVD47",2),
        _scale("pv.irradiance","PVSystem.PVD76",.2),
    )
    engine=ForecastNoiseEngine(ForecastNoiseSpec("additive_gaussian",3,scales=scales),
                               explicit_source=source,reset_seed=clock.reset_seed)
    out,audit=engine.transform(oracle.request(0,2))
    for lead in (0,1):
        g=_value(out,lead,"pv.irradiance","PVSystem.PVD47").value
        ta=_value(out,lead,"pv.outdoor_temperature","PVSystem.PVD47").value
        wind=_value(out,lead,"pv.wind_speed","PVSystem.PVD47").value
        temp=_value(out,lead,"pv.cell_temperature","PVSystem.PVD47").value
        assert wind>=0 and g>=0
        assert temp==pytest.approx(ta+1000*g/(25+6.84*wind))
        assert _value(out,lead,"pv.cell_temperature","PVSystem.PVD76").value==25
    assert len(audit)==8


def test_strict_horizon_errors_before_noise_and_invalid_configs():
    oracle,spec,clock=_oracle(mode="strict")
    from opendsssim.environment import ForecastCoverageError
    with pytest.raises(ForecastCoverageError):oracle.request(2,2)
    with pytest.raises(ForecastNoiseError):ForecastNoiseSpec("normal",seed=1)
    with pytest.raises(ForecastNoiseError):ForecastNoiseSpec("additive_gaussian",seed=None,scales=(_scale("load.kw"),))
    with pytest.raises(ForecastNoiseError):GaussianScale("load.kw","Load.S1a",sigma=-1)
    with pytest.raises(ForecastNoiseError):GaussianScale("load.kw","Load.S1a",sigma=float("nan"))
    with pytest.raises(ForecastNoiseError):ForecastNoiseSpec("additive_gaussian",seed=True,scales=(_scale("load.kw"),))
    with pytest.raises(ForecastNoiseError):ForecastNoiseSpec("additive_gaussian",seed=4,scales=(
        _scale("load.kw"),_scale("load.kw")))
    misconfigured=ForecastNoiseSpec("additive_gaussian",seed=4,scales=(_scale("load.other"),))
    with pytest.raises(ForecastNoiseError):ForecastNoiseEngine(misconfigured).validate_declared(oracle.request(0,1))
