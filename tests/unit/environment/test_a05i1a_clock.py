"""A05I1A pure clock contracts: no backend dependencies required by the clock."""
from datetime import datetime, timezone

import pytest

from opendsssim.environment.clock import EpisodeClock, EpisodeClockError, EpisodeSpec


def test_clock_option_a_reset_and_first_step_time_identity():
    spec = EpisodeSpec(start_time_utc="2026-10-27T15:30:00-07:00", dt_seconds=900, max_steps=2)
    assert spec.start_time_utc == datetime(2026, 10, 27, 22, 30, tzinfo=timezone.utc)
    clock = EpisodeClock(spec, "episode-000001", 42)
    reset = clock.metadata(phase="reset", completed_steps=0)
    step1 = clock.metadata(phase="step", completed_steps=1)
    step2 = clock.metadata(phase="step", completed_steps=2)
    assert reset["electrical_sample_time_utc"] == step1["electrical_sample_time_utc"]
    assert step1["electrical_sample_time_utc"] != step1["decision_time_utc"]
    assert step1["decision_time_utc"] == step2["electrical_sample_time_utc"]
    assert step1["completed_steps"] == 1
    assert clock.is_horizon_exhausted(1) is False
    assert clock.is_horizon_exhausted(2) is True
    assert reset["clock_authority"] == "EXTERNAL"
    assert reset["engine_time_status"] == "EXTERNAL_ONLY_NOT_MIRRORED"


@pytest.mark.parametrize("kwargs", [
    {"start_time_utc": "2026-11-01T01:30:00"},  # Ambiguous local/DST time.
    {"start_time_utc": "not-a-date"},
    {"dt_seconds": 0},
    {"dt_seconds": float("nan")},
    {"dt_seconds": float("inf")},
    {"dt_seconds": True},
    {"max_steps": 0},
    {"max_steps": -1},
    {"max_steps": True},
    {"max_steps": 1.5},
])
def test_clock_rejects_invalid_parameters(kwargs):
    with pytest.raises(EpisodeClockError):
        EpisodeSpec(**kwargs)


def test_generic_defaults_and_reset_options():
    default = EpisodeSpec()
    assert default.start_time_utc.isoformat() == "2000-01-01T00:00:00+00:00"
    assert default.dt_seconds == 3600
    assert default.max_steps is None
    chosen = default.with_reset_options({"max_steps": 1, "start_time_utc": "2026-10-28T00:00:00Z"})
    assert chosen.max_steps == 1
    assert chosen.start_time_utc.isoformat() == "2026-10-28T00:00:00+00:00"
    assert default.max_steps is None  # No mutation of the constructor configuration.
    with pytest.raises(EpisodeClockError, match="Unsupported"):
        default.with_reset_options({"topology_event": "OPEN"})


def test_clock_is_not_an_altdss_engine_clock():
    clock = EpisodeClock(EpisodeSpec(dt_seconds=60), "episode-000001", None)
    info = clock.metadata(phase="step", completed_steps=1)
    assert info["exogenous_sample_status"] == "NO_A05_SOURCE_BOUND"
    assert info["interval_start_utc"] == "2000-01-01T00:00:00+00:00"
    assert info["interval_end_utc"] == "2000-01-01T00:01:00+00:00"
    with pytest.raises(EpisodeClockError):
        clock.metadata(phase="step", completed_steps=0)
