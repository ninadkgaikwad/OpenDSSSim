"""Deterministic source identity and atomic runtime-manifest writing."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
import tempfile
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Iterable

from opendsssim import (
    ARCHITECTURE_DOCUMENT_ID,
    PATCH_ID,
    PRE_A01_SOURCE_MANIFEST_SHA256,
)
from opendsssim.persistence.schema import RuntimeManifest


_EXCLUDED_PARTS = {".git", "__pycache__", ".pytest_cache"}


def _iter_source_files(repo_root: Path) -> Iterable[Path]:
    for path in sorted(repo_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(repo_root)
        if any(part in _EXCLUDED_PARTS for part in relative.parts):
            continue
        yield path


def compute_source_identity(repo_root: str | Path) -> str:
    """Compute a deterministic digest over repository file paths and bytes."""

    root = Path(repo_root).resolve()
    h = hashlib.sha256()
    for path in _iter_source_files(root):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        data = path.read_bytes()
        file_hash = hashlib.sha256(data).hexdigest().upper().encode("ascii")
        record = (
            relative
            + b"\0"
            + str(len(data)).encode("ascii")
            + b"\0"
            + file_hash
            + b"\n"
        )
        h.update(record)
    return h.hexdigest().upper()


def write_runtime_manifest(
    destination: str | Path,
    *,
    repo_root: str | Path,
    engine_version: str,
    context_identity: int,
    machine_role: str = "development-laptop",
) -> RuntimeManifest:
    """Write one runtime manifest atomically and return its typed schema."""

    manifest = RuntimeManifest(
        patch_id=PATCH_ID,
        architecture_document_id=ARCHITECTURE_DOCUMENT_ID,
        predecessor_source_manifest_sha256=PRE_A01_SOURCE_MANIFEST_SHA256,
        current_source_identity_sha256=compute_source_identity(repo_root),
        machine_role=machine_role,
        python_version=platform.python_version(),
        altdss_version=package_version("altdss"),
        engine_version=str(engine_version),
        context_identity=int(context_identity),
    )

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(
        prefix=destination.name + ".",
        suffix=".tmp",
        dir=str(destination.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(manifest.to_dict(), handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp_name, destination)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise

    return manifest
