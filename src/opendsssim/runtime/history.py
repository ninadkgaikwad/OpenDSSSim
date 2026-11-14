"""Append-only A04I3 in-memory history with independent retention levels."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

import numpy as np

from .schema import ExecutionProfile, HistoryLevel, RuntimeStepContext


def _plain_copy(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain_copy(item) for key, item in value.items()}
    if isinstance(value, np.ndarray):
        return value.copy()
    if isinstance(value, tuple):
        return tuple(_plain_copy(item) for item in value)
    if isinstance(value, list):
        return [_plain_copy(item) for item in value]
    return value


@dataclass
class RuntimeHistory:
    level: HistoryLevel = HistoryLevel.H1
    execution_profile: ExecutionProfile = ExecutionProfile.STANDARD
    _records: list[dict[str, Any]] = field(default_factory=list, init=False, repr=False)

    def clear(self) -> None:
        self._records.clear()

    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self) -> Iterable[dict[str, Any]]:
        return iter(self._records)

    def __getitem__(self, index: int) -> dict[str, Any]:
        return self._records[index]

    @property
    def records(self) -> tuple[dict[str, Any], ...]:
        return tuple(_plain_copy(self._records))

    def append(
        self,
        context: RuntimeStepContext,
        *,
        phase: str,
        reward: float | None,
        terminated: bool | None,
        truncated: bool | None,
        info: dict[str, Any],
        full_state: dict[str, Any] | None = None,
    ) -> None:
        record: dict[str, Any] = {
            "phase": phase,
            "step_index": context.step_index,
            "converged": bool(context.solution.get("converged", False)),
            "observation": _plain_copy(context.observation),
            "action_status": [item.to_dict() for item in context.action_audit],
            "reward": reward,
            "terminated": terminated,
            "truncated": truncated,
        }
        if self.level in {HistoryLevel.H1, HistoryLevel.H2, HistoryLevel.H3}:
            record.update({
                "requested_action": _plain_copy(context.requested_action),
                "applied_action": _plain_copy(context.applied_action),
                "realized_action": _plain_copy(context.realized_action),
                "internal_state": _plain_copy(context.internal_state),
                "disturbances": _plain_copy(context.disturbances),
                "parameters": _plain_copy(context.parameters),
                "constraints": _plain_copy(context.constraints),
                "availability": _plain_copy(context.availability),
                "authority": _plain_copy(context.authority),
                "solution": _plain_copy(context.solution),
            })
        if self.level in {HistoryLevel.H2, HistoryLevel.H3}:
            record["full_state"] = _plain_copy(full_state or {})
        if self.level is HistoryLevel.H3:
            record["info"] = _plain_copy(info)
        self._records.append(record)
