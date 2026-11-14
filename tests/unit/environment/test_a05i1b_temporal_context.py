"""Pure A05I1B temporal-context regression and immutable view tests."""
from dataclasses import FrozenInstanceError
from types import MappingProxyType

import pytest

from opendsssim.environment import TemporalRuntimeStepContext
from opendsssim.runtime import RuntimeStepContext


def _context(time):
    return TemporalRuntimeStepContext.create(
        time=time,
        step_index=1,
        observation={"obs": {"converged": 1}},
        requested_action={}, applied_action={}, realized_action={},
        action_audit=(), internal_state={}, disturbances={}, parameters={},
        constraints={}, availability={}, authority={"mode": "NATIVE"},
        solution={"converged": True}, previous_observation=None,
    )


def test_temporal_context_preserves_frozen_a04_type_and_data():
    original = {"phase": "step", "completed_steps": 1,
                "electrical_sample_time_utc": "2026-10-28T00:00:00+00:00",
                "decision_time_utc": "2026-10-28T01:00:00+00:00",
                "source": {"channel_ids": ["load-a", "pv-b"]}}
    context = _context(original)
    assert isinstance(context, RuntimeStepContext)
    assert context.time["completed_steps"] == context.step_index
    assert isinstance(context.time, MappingProxyType)
    assert isinstance(context.observation["obs"], MappingProxyType)
    assert context.time["source"]["channel_ids"] == ("load-a", "pv-b")

    original["completed_steps"] = 99
    original["source"]["channel_ids"].append("unapproved")
    assert context.time["completed_steps"] == 1
    assert context.time["source"]["channel_ids"] == ("load-a", "pv-b")
    with pytest.raises(TypeError):
        context.time["completed_steps"] = 77
    with pytest.raises(TypeError):
        context.time["source"]["channel_ids"] += ("unapproved",)
    with pytest.raises(FrozenInstanceError):
        context.time = {}


def test_temporal_context_requires_json_shaped_readonly_clock_data():
    with pytest.raises(TypeError, match="requires time metadata"):
        _context(None)
    with pytest.raises(TypeError, match="Unsupported temporal metadata"):
        _context({"unsafe": object()})
