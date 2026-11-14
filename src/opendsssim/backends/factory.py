"""Backend construction."""

from __future__ import annotations

from opendsssim.backends.altdss_backend import AltDSSBackend
from opendsssim.backends.base import DistributionBackend


def create_backend(name: str = "altdss") -> DistributionBackend:
    normalized = name.strip().lower()
    if normalized == "altdss":
        return AltDSSBackend()
    raise ValueError(f"Unsupported backend {name!r}. A01 supports only 'altdss'.")
