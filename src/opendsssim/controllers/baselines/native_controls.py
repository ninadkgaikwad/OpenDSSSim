"""B00 reusable native-as-installed controller: NEVER writes electrical state.

This adapter consumes only the A05I6 detached controller snapshot and the A04
Gym action space. It has no AltDSS, Plant or native-property dependency.
"""
from __future__ import annotations

from typing import Any


class NativeBaselineContractError(RuntimeError):
    """B00 cannot safely operate against an externally controlled action layout."""


class NativeControlsBaseline:
    """Choose the empty A04 action when the simulator retains native authority."""

    controller_id = "B00.NATIVE_AS_INSTALLED.V01"

    def action(self, *, context: Any, action_space: Any) -> dict[str, Any]:
        if context is None or not hasattr(context, "action_layout"):
            raise NativeBaselineContractError("A05I6_CONTROLLER_CONTEXT_REQUIRED")
        if tuple(context.action_layout):
            raise NativeBaselineContractError("B00_EXTERNAL_ACTION_LAYOUT_FORBIDDEN")
        if not action_space.contains({}):
            raise NativeBaselineContractError("B00_EMPTY_ACTION_NOT_AUTHORIZED")
        # Always allocate a fresh empty mapping. No native writes or backend handle.
        return {}
