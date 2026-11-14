"""Stable importable hook callables for A04I3 qualification tests."""

def configured_reward(context, scale=1.0):
    return float(scale) * float(context.step_index)

def terminate_after_one(context):
    return context.step_index >= 1

def never_truncate(context):
    return False

def invalid_reward(context):
    return float("nan")
