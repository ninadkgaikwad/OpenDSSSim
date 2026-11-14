"""Typed snapshot-solution result."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SolutionResult:
    """Immutable status/result summary for one snapshot solution."""

    converged: bool
    iterations: int
    total_iterations: int
    control_iterations: int
    process_time_s: float
    solve_mode: str
    circuit_name: str
    num_buses: int
    num_nodes: int
    num_circuit_elements: int
    total_power_kw: float
    total_power_kvar: float
    engine_version: str
    altdss_version: str
    context_identity: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
