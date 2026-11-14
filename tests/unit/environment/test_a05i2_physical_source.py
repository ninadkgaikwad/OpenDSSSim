"""A05I2 typed physical truth and source validation, with no native engine required."""
import math
import pytest

from opendsssim.environment.exogenous import (
    ExogenousProfileSpec, LoadSeries, PVSeries, ExogenousBindingError,
)


def test_load_modes_and_fanout_are_immutable_and_hashed():
    points = [[100, 40], [80, 32]]
    series = LoadSeries(("Load.S1a", "Load.S2b"), "absolute_pq", points)
    points[0][0] = 999
    assert series.points == ((100.0, 40.0), (80.0, 32.0))
    spec = ExogenousProfileSpec("test-source", (series,))
    assert len(spec.source_sha256) == 64 and spec.sample_count == 2
    assert spec.source_sha256 == ExogenousProfileSpec("test-source", (series,)).source_sha256
    assert spec.source_sha256 != ExogenousProfileSpec("changed-source", (series,)).source_sha256


def test_modes_have_strict_physical_units_and_domains():
    assert LoadSeries(("Load.S1a",), "multiplier", [0.7]).points == (0.7,)
    assert LoadSeries(("Load.S1a",), "p_signed_pf", [(50, -0.8)]).points == ((50.0, -0.8),)
    for mode, points in (
        ("multiplier", [-0.1]),
        ("multiplier", [float("nan")]),
        ("p_signed_pf", [(50, 0)]),
        ("p_signed_pf", [(50, 1.01)]),
        ("p_signed_pf", [(-30, 0.8)]),
        ("absolute_pq", [(float("inf"), 0)]),
        ("absolute_pq", [(2, "untyped")]),
    ):
        with pytest.raises(ExogenousBindingError):
            LoadSeries(("Load.S1a",), mode, points)
    with pytest.raises(ExogenousBindingError):
        LoadSeries(("Load.S1a",), "pf_only", [0.9])


def test_pv_temperature_modes_and_reject_incomplete_weather():
    pv = PVSeries(("PVSystem.PVD47",), (0.8, 0.0),
                  outdoor_temperature_c=(20, 19), wind_speed_m_s=(5, 0))
    assert pv.u0 == 25.0 and pv.u1 == 6.84
    assert math.isclose(20 + 800 / (25 + 6.84 * 5), 33.5135, rel_tol=1e-3)
    constant = PVSeries(("PVSystem.PVD47",), (1.0,))
    assert constant.outdoor_temperature_c is None
    with pytest.raises(ExogenousBindingError):
        PVSeries(("PVSystem.PVD47",), (1.0,), outdoor_temperature_c=(30,))
    with pytest.raises(ExogenousBindingError):
        PVSeries(("PVSystem.PVD47",), (1.0,), outdoor_temperature_c=(30,), wind_speed_m_s=(-1,))
    with pytest.raises(ExogenousBindingError):
        PVSeries(("PVSystem.PVD47",), (1.0,), outdoor_temperature_c=(30,), wind_speed_m_s=())
    with pytest.raises(ExogenousBindingError):
        PVSeries(("PVSystem.PVD47",), (1.0,), u0=0)


def test_samples_are_strict_and_native_writers_must_be_unique():
    a = LoadSeries(("Load.S1a",), "multiplier", (1.0, 0.8))
    with pytest.raises(ExogenousBindingError, match="identical sample count"):
        ExogenousProfileSpec("wrong-length", (a,), (PVSeries(("PVSystem.X",), (1.0,)),))
    with pytest.raises(ExogenousBindingError, match="ambiguous exogenous writers"):
        ExogenousProfileSpec("duplicate", (a, LoadSeries(("load.s1A",), "multiplier", (1.0, 1.0))))
    with pytest.raises(ExogenousBindingError):
        ExogenousProfileSpec("empty")
    with pytest.raises(ExogenousBindingError):
        LoadSeries(("Load.S1a", "load.s1A"), "multiplier", (1.0,))
