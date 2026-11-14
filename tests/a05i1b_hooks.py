"""Imported test hooks exercise the frozen A04 hook interface with A05 time."""


def reward_from_time(context):
    assert context.time["phase"] == "step"
    assert context.time["clock_authority"] == "EXTERNAL"
    assert context.time["completed_steps"] == context.step_index
    assert context.time["interval_start_utc"] == context.time["electrical_sample_time_utc"]
    assert context.time["interval_end_utc"] == context.time["decision_time_utc"]
    return float(context.time["completed_steps"])


def terminate_second_step(context):
    return context.time["completed_steps"] == 2


def never_truncate(context):
    return False


def illegal_time_mutation(context):
    context.time["completed_steps"] = 100
    return 0.0
