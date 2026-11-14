"""Backend contracts for OpenDSSSim."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from opendsssim.discovery.schema import CircuitDiscovery, EngineDiscovery
from opendsssim.network.loading import CircuitIdentity, CircuitSource
from opendsssim.plant.solution import SolutionResult


class OpenDSSSimBackendError(RuntimeError):
    """Base backend error."""


class CircuitNotLoadedError(OpenDSSSimBackendError):
    """Raised when a circuit-dependent operation occurs before circuit loading."""


class DistributionBackend(ABC):
    """Electrical-network backend contract through A04I2 runtime access."""

    @property
    @abstractmethod
    def context_identity(self) -> int:
        """Process-local identity of the owned backend context."""

    @property
    @abstractmethod
    def engine_version(self) -> str:
        """Backend engine version string."""

    @property
    @abstractmethod
    def loaded_source(self) -> CircuitSource | None:
        """Currently loaded circuit source, if any."""

    @property
    @abstractmethod
    def is_closed(self) -> bool:
        """Whether this backend has been closed."""

    @abstractmethod
    def load_circuit(self, source: CircuitSource) -> CircuitIdentity:
        """Clear this owned context and load one circuit."""

    @abstractmethod
    def reset_circuit(self) -> CircuitIdentity:
        """Deterministically clear and reload the previously loaded circuit."""

    @abstractmethod
    def solve_snapshot(self) -> SolutionResult:
        """Execute one authoritative snapshot power-flow solve."""

    @abstractmethod
    def discover_engine(self) -> EngineDiscovery:
        """Return a typed, read-only snapshot of engine capabilities."""

    @abstractmethod
    def discover_circuit(self) -> CircuitDiscovery:
        """Return a typed, read-only snapshot of the loaded circuit."""

    @abstractmethod
    def read_object_properties(
        self,
        object_full_name: str,
        property_names: tuple[str, ...],
    ) -> dict[str, Any]:
        """Read explicit native object properties without broad circuit discovery."""

    @abstractmethod
    def write_object_property(
        self,
        object_full_name: str,
        property_name: str,
        value: Any,
    ) -> Any:
        """Write one explicit native property and return the authoritative readback."""

    @abstractmethod
    def read_runtime_channel(
        self,
        service: str,
        entity: str | None,
        channel: str,
    ) -> Any:
        """Read one qualified runtime channel identified by A03 semantics."""

    @abstractmethod
    def apply_runtime_command(
        self,
        service: str,
        entity: str,
        operation: str,
        value: Any,
    ) -> Any:
        """Apply one qualified runtime command and return authoritative post-command state."""

    @abstractmethod
    def close(self) -> None:
        """Release references/resources owned by the backend."""
