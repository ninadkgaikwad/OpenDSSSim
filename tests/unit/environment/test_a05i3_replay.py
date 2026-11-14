"""A05I3 source-time and replay contract tests, no AltDSS required."""
from datetime import datetime, timezone
from hashlib import sha256
import csv
import pytest

from opendsssim.environment.replay import (
    ReplaySource, ReplayBinding, ReplaySpec, ReplaySession, ReplayTable,
    ReplayValidationError,
)


def _csv(path, rows, header=("timestamp", "p", "q")):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def _binding(source="s", mode="absolute_pq", cols=("p", "q"), units=("kW", "kvar"), **kw):
    return ReplayBinding(source, "load", ("Load.S1a",), mode, cols, units, **kw)


def _spec(path, *, dt=None, mode="tile", max_steps=6, bindings=None):
    return ReplaySpec((ReplaySource("s", "timestamp", "UTC", path=path),),
                      (_binding() if bindings is None else bindings,), mode=mode,
                      dt_seconds=dt, max_steps=max_steps)


def test_tile_and_strict_last_valid_sample_clock_provenance(tmp_path):
    p = _csv(tmp_path / "a.csv", [
        ("2026-01-01T00:00:00Z", 10, 3),
        ("2026-01-01T01:00:00Z", 20, 6),
        ("2026-01-01T02:00:00Z", 30, 9),
    ])
    tile = ReplaySession(_spec(p))
    assert tile.episode_spec.dt_seconds == 3600
    assert tile.episode_spec.start_time_utc == datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert [tile.sample(k)[0].loads[0].points[0][0] for k in range(7)] == [10,20,30,10,20,30,10]
    assert tile.sample(3)[1]["sources"][0]["replay_cycle"] == 1
    assert tile.sample(3)[1]["sources"][0]["source_timestamp_utc"] == "2026-01-01T00:00:00+00:00"
    strict = ReplaySession(_spec(p, mode="strict", max_steps=10))
    assert strict.strict_sample_count == 3
    assert strict.last_strict_index(2) and not strict.last_strict_index(1)
    with pytest.raises(ReplayValidationError, match="EXHAUSTED"):
        strict.sample(3)


def test_mixed_cadence_requires_explicit_dt_and_declared_resample(tmp_path):
    a = _csv(tmp_path / "a.csv", [("2026-01-01T00:00:00Z",10,3), ("2026-01-01T01:00:00Z",30,9)])
    b = _csv(tmp_path / "b.csv", [("2026-01-01T00:00:00Z",1), ("2026-01-01T00:30:00Z",2), ("2026-01-01T01:00:00Z",3)], ("timestamp", "mult"))
    sources = (ReplaySource("s", "timestamp", "UTC", a), ReplaySource("t", "timestamp", "UTC", b))
    bind = (_binding(interpolation="linear"), ReplayBinding("t", "load", ("Load.S2b",), "multiplier", ("mult",), ("pu",)))
    with pytest.raises(ReplayValidationError, match="common cadence"):
        ReplaySession(ReplaySpec(sources, bind))
    sess = ReplaySession(ReplaySpec(sources, bind, dt_seconds=1800, mode="tile"))
    assert [sess.sample(k)[0].loads[0].points[0][0] for k in range(3)] == [10,20,30]
    assert sess.sample(1)[1]["sources"][0]["operation"] == "linear"
    assert sess.sample(1)[1]["sources"][0]["linear_weight"] == 0.5
    with pytest.raises(ReplayValidationError, match="gap"):
        ReplaySession(ReplaySpec(sources, (_binding(interpolation="linear", max_gap_seconds=1000), bind[1]), dt_seconds=1800))


def test_zero_order_hold_and_bad_units_and_no_extrapolation(tmp_path):
    p = _csv(tmp_path / "p.csv", [("2026-01-01T00:00:00Z", 1), ("2026-01-01T01:00:00Z", 3)], ("timestamp", "mult"))
    b = _binding(mode="multiplier", cols=("mult",), units=("pu",), interpolation="hold")
    s = ReplaySession(_spec(p, dt=1800, bindings=b))
    assert [s.sample(i)[0].loads[0].points[0] for i in range(3)] == [1,1,3]
    with pytest.raises(ReplayValidationError, match="units"):
        _binding(mode="absolute_pq", units=("kWh", "kvar"))
    with pytest.raises(ReplayValidationError, match="jointly valid sample"):
        ReplaySession(_spec(p, dt=1800, bindings=b), options={"start_time_utc": "2026-01-01T02:00:00Z"})


def test_dst_ambiguous_duplicate_and_invalid_data_rejected(tmp_path):
    b = _binding()
    for rows, tz, message in [
        ([("2026-11-01T01:30:00", 10, 1), ("2026-11-01T02:30:00", 20, 2)], "America/Los_Angeles", "DST"),
        ([("2026-01-01T00:00:00Z",10,1), ("2026-01-01T00:00:00Z",20,2)], "UTC", "duplicate"),
        ([("2026-01-01T00:00:00Z",10,1), ("2026-01-01T01:00:00Z",float('nan'),2)], "UTC", "finite"),
    ]:
        p=_csv(tmp_path / "bad.csv", rows)
        s=ReplaySpec((ReplaySource("s", "timestamp", tz, p),), (b,), dt_seconds=3600)
        with pytest.raises(ReplayValidationError if message != "finite" else Exception):
            ReplaySession(s)


def test_custom_reader_typed_table_and_hash_identity():
    def tab(n):
        return ReplayTable(("2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z"),
                           {"m": (1.0, n)}, sha256(f"source:{n}".encode()).hexdigest())
    src = lambda n: ReplaySource("s", "timestamp", "UTC", table=tab(n))
    b = _binding(mode="multiplier", cols=("m",), units=("pu",))
    s1 = ReplaySession(ReplaySpec((src(0.8),), (b,)))
    s2 = ReplaySession(ReplaySpec((src(0.6),), (b,)))
    assert s1.identity_sha256 != s2.identity_sha256
    assert s1.sample(1)[0].loads[0].points == (0.8,)


def test_parquet_csv_parity_when_pyarrow_available(tmp_path):
    pa = pytest.importorskip("pyarrow")
    import pyarrow.parquet as pq
    rows = [("2026-01-01T00:00:00Z",10,1), ("2026-01-01T01:00:00Z",20,2)]
    csvfile = _csv(tmp_path / "s.csv", rows)
    parquet = tmp_path / "s.parquet"
    pq.write_table(pa.table({"timestamp": [x[0] for x in rows], "p": [x[1] for x in rows], "q": [x[2] for x in rows]}), parquet)
    sa = ReplaySession(_spec(csvfile))
    sb = ReplaySession(_spec(parquet))
    assert [sa.sample(i)[0].loads[0].points for i in range(2)] == [sb.sample(i)[0].loads[0].points for i in range(2)]


def test_first_joint_timestamp_preserves_full_source_tile_period(tmp_path):
    a = _csv(tmp_path / "a.csv", [(f"2026-01-01T0{i}:00:00Z", 10+i, 1) for i in range(4)])
    b = _csv(tmp_path / "b.csv", [(f"2026-01-01T0{i}:00:00Z", i) for i in range(1,4)], ("timestamp", "mult"))
    sess = ReplaySession(ReplaySpec(
        (ReplaySource("s", "timestamp", "UTC", a), ReplaySource("t", "timestamp", "UTC", b)),
        (_binding(), ReplayBinding("t", "load", ("Load.S2b",), "multiplier", ("mult",), ("pu",))),
        dt_seconds=3600,
    ))
    assert sess.episode_spec.start_time_utc.hour == 1
    assert [sess.sample(k)[0].loads[0].points[0][0] for k in range(4)] == [11,12,13,10]
    assert [sess.sample(k)[0].loads[1].points[0] for k in range(4)] == [1,2,3,1]
    assert sess.sample(3)[1]["sources"][0]["replay_cycle"] == 1
    assert sess.sample(3)[1]["sources"][1]["replay_cycle"] == 1
    strict = ReplaySession(ReplaySpec(
        (ReplaySource("s", "timestamp", "UTC", a), ReplaySource("t", "timestamp", "UTC", b)),
        (_binding(), ReplayBinding("t", "load", ("Load.S2b",), "multiplier", ("mult",), ("pu",))),
        mode="strict", dt_seconds=3600,
    ))
    assert strict.strict_sample_count == 3


def test_pv_irradiance_and_faiman_weather_preserved(tmp_path):
    p = _csv(tmp_path / "p.csv", [
        ("2026-01-01T00:00:00Z",0.8,20,5),
        ("2026-01-01T01:00:00Z",0.5,21,4)],
        ("timestamp", "poa", "ambient", "wind"))
    pv = ReplayBinding("s", "pv", ("PVSystem.PVD47",), "irradiance_faiman",
                       ("poa", "ambient", "wind"), ("kW/m2", "degC", "m/s"))
    session = ReplaySession(ReplaySpec((ReplaySource("s", "timestamp", "UTC", p),), (pv,)))
    physical, meta = session.sample(0)
    assert physical.pvs[0].irradiance_kw_m2 == (0.8,)
    assert physical.pvs[0].outdoor_temperature_c == (20.0,)
    assert physical.pvs[0].wind_speed_m_s == (5.0,)
    assert meta["sources"][0]["source_sha256"] == sha256(p.read_bytes()).hexdigest().upper()
