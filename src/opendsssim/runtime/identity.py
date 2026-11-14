"""Deterministic A04I3 implementation/runtime identity helpers."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping


def canonical_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256(encoded).hexdigest().upper()


def package_source_sha256(package_root: str | Path | None = None) -> str:
    root = Path(package_root).resolve() if package_root is not None else Path(__file__).resolve().parents[1]
    digest = sha256()
    for path in sorted(root.rglob("*.py"), key=lambda p: p.relative_to(root).as_posix().casefold()):
        rel = path.relative_to(root).as_posix().encode("utf-8")
        data = path.read_bytes()
        digest.update(len(rel).to_bytes(8, "big")); digest.update(rel)
        digest.update(len(data).to_bytes(8, "big")); digest.update(data)
    return digest.hexdigest().upper()
