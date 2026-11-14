"""Persistence schemas for A01 provenance."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class RuntimeManifest:
    patch_id: str
    architecture_document_id: str
    predecessor_source_manifest_sha256: str
    current_source_identity_sha256: str
    machine_role: str
    python_version: str
    altdss_version: str
    engine_version: str
    context_identity: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
