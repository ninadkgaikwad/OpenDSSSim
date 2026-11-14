"""A04I2 execution of frozen A03 semantic addresses.

This module is intentionally mechanism-only. It does not decide whether a
channel is controller-visible or writable in a particular ProblemSpec; A04I3
runtime binding owns those authorization decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from opendsssim.backends.base import DistributionBackend
from opendsssim.semantics.schema import (
    NativePropertyAddress,
    RuntimeCommandAddress,
    RuntimeReadoutAddress,
    SemanticAddress,
)


class SemanticRuntimeAccessError(RuntimeError):
    """Raised when a semantic address is used with an invalid access direction."""


def _casefold_lookup(values: dict[str, Any], requested: str) -> Any:
    key = str(requested).casefold()
    for name, value in values.items():
        if str(name).casefold() == key:
            return value
    raise SemanticRuntimeAccessError(
        f"Backend did not return requested native property {requested!r}."
    )


@dataclass(frozen=True, slots=True)
class SemanticRuntimeAccess:
    """Execute A03 semantic addresses against one backend instance."""

    backend: DistributionBackend

    def read(self, address: SemanticAddress) -> Any:
        """Read a native property or runtime readout exactly as addressed by A03."""

        if isinstance(address, NativePropertyAddress):
            values = self.backend.read_object_properties(
                address.object_full_name,
                (address.property_name,),
            )
            return _casefold_lookup(values, address.property_name)

        if isinstance(address, RuntimeReadoutAddress):
            return self.backend.read_runtime_channel(
                address.service,
                address.entity,
                address.channel,
            )

        if isinstance(address, RuntimeCommandAddress):
            raise SemanticRuntimeAccessError(
                "RuntimeCommandAddress is write-only and cannot be read directly."
            )

        raise TypeError(f"Unsupported semantic address type: {type(address).__name__}")

    def write(self, address: SemanticAddress, value: Any) -> Any:
        """Write a native property or apply a runtime command exactly as addressed by A03."""

        if isinstance(address, NativePropertyAddress):
            return self.backend.write_object_property(
                address.object_full_name,
                address.property_name,
                value,
            )

        if isinstance(address, RuntimeCommandAddress):
            return self.backend.apply_runtime_command(
                address.service,
                address.entity,
                address.operation,
                value,
            )

        if isinstance(address, RuntimeReadoutAddress):
            raise SemanticRuntimeAccessError(
                "RuntimeReadoutAddress is read-only and cannot be written."
            )

        raise TypeError(f"Unsupported semantic address type: {type(address).__name__}")


def read_semantic_address(backend: DistributionBackend, address: SemanticAddress) -> Any:
    """Convenience functional API for one semantic read."""

    return SemanticRuntimeAccess(backend).read(address)


def write_semantic_address(
    backend: DistributionBackend,
    address: SemanticAddress,
    value: Any,
) -> Any:
    """Convenience functional API for one semantic write/command."""

    return SemanticRuntimeAccess(backend).write(address, value)
