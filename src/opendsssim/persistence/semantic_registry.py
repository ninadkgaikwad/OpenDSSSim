"""Persistent A03 SemanticRegistryBundle cache and validation."""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from opendsssim.persistence.inventory_schema import CircuitInventory
from opendsssim.semantics.policy import SEMANTIC_POLICY_SHA256
from opendsssim.semantics.schema import (
    SEMANTIC_POLICY_VERSION,
    SEMANTIC_REGISTRY_SCHEMA_VERSION,
    SemanticRegistryBundle,
)


class SemanticRegistryInvalidError(RuntimeError):
    """Raised when a persisted A03 semantic bundle is malformed or invalid."""


def default_semantic_registry_dir() -> Path:
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        return Path(local_appdata).expanduser().resolve() / "OpenDSSSim" / "semantic_registry"
    return Path.home().expanduser().resolve() / ".opendssim" / "semantic_registry"


def _safe_stem(value: str) -> str:
    chars = [ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value]
    stem = "".join(chars).strip("_")
    return stem or "circuit"


def semantic_registry_cache_key(
    inventory: CircuitInventory,
    *,
    registry_schema_version: str = SEMANTIC_REGISTRY_SCHEMA_VERSION,
    semantic_policy_version: str = SEMANTIC_POLICY_VERSION,
    semantic_policy_sha256: str = SEMANTIC_POLICY_SHA256,
) -> str:
    payload = {
        "registry_schema_version": registry_schema_version,
        "semantic_policy_version": semantic_policy_version,
        "semantic_policy_sha256": semantic_policy_sha256,
        "source_inventory_semantic_sha256": inventory.semantic_sha256,
        "source_tree_sha256": inventory.source_tree_sha256,
        "backend": inventory.backend,
        "altdss_version": inventory.altdss_version,
        "engine_version": inventory.engine_version,
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest().upper()


def semantic_registry_path_for_inventory(
    inventory: CircuitInventory,
    *,
    semantic_registry_dir: str | Path | None = None,
) -> Path:
    root = (
        Path(semantic_registry_dir).expanduser().resolve()
        if semantic_registry_dir is not None
        else default_semantic_registry_dir()
    )
    key = semantic_registry_cache_key(inventory)
    stem = _safe_stem(Path(inventory.master_relative_path).stem)
    return root / f"{stem}__{key[:24]}.json"


def write_semantic_registry_bundle(
    destination: str | Path,
    bundle: SemanticRegistryBundle,
) -> Path:
    destination = Path(destination).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(
        prefix=destination.name + ".",
        suffix=".tmp",
        dir=str(destination.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(bundle.to_json())
        os.replace(tmp_name, destination)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise

    return destination


def read_semantic_registry_bundle(
    path: str | Path,
) -> SemanticRegistryBundle:
    path = Path(path).expanduser().resolve()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SemanticRegistryInvalidError(
            f"Unable to read semantic registry bundle: {path}"
        ) from exc

    if not isinstance(payload, dict):
        raise SemanticRegistryInvalidError(
            f"Expected semantic registry JSON object: {path}"
        )

    try:
        return SemanticRegistryBundle.from_dict(payload)
    except (KeyError, TypeError, ValueError) as exc:
        raise SemanticRegistryInvalidError(
            f"Invalid semantic registry bundle: {path}"
        ) from exc


def validate_bundle_for_inventory(
    bundle: SemanticRegistryBundle,
    inventory: CircuitInventory,
    *,
    registry_schema_version: str = SEMANTIC_REGISTRY_SCHEMA_VERSION,
    semantic_policy_version: str = SEMANTIC_POLICY_VERSION,
    semantic_policy_sha256: str = SEMANTIC_POLICY_SHA256,
) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []

    checks: dict[str, tuple[Any, Any]] = {
        "registry_schema_version": (
            bundle.registry_schema_version,
            registry_schema_version,
        ),
        "semantic_policy_version": (
            bundle.semantic_policy_version,
            semantic_policy_version,
        ),
        "semantic_policy_sha256": (
            bundle.semantic_policy_sha256,
            semantic_policy_sha256,
        ),
        "source_inventory_semantic_sha256": (
            bundle.source_inventory_semantic_sha256,
            inventory.semantic_sha256,
        ),
        "source_tree_sha256": (
            bundle.source_tree_sha256,
            inventory.source_tree_sha256,
        ),
        "backend": (bundle.backend, inventory.backend),
        "altdss_version": (bundle.altdss_version, inventory.altdss_version),
        "engine_version": (bundle.engine_version, inventory.engine_version),
    }

    for name, (actual, expected) in checks.items():
        if actual != expected:
            reasons.append(
                f"{name}: expected={expected!r} actual={actual!r}"
            )

    entry_ids = {item.semantic_id for item in bundle.semantic_entries}
    if len(entry_ids) != len(bundle.semantic_entries):
        reasons.append("semantic_entries: duplicate semantic_id")

    for registry_name, entry_ids_view in (
        ("state_registry", bundle.state_registry.entry_ids),
        ("action_registry", bundle.action_registry.entry_ids),
        ("disturbance_registry", bundle.disturbance_registry.entry_ids),
        ("constraint_registry", bundle.constraint_registry.entry_ids),
        ("parameter_registry", bundle.parameter_registry.entry_ids),
    ):
        missing = sorted(set(entry_ids_view) - entry_ids)
        if missing:
            reasons.append(
                f"{registry_name}: references missing semantic IDs {missing}"
            )

    return (not reasons), tuple(reasons)


def load_valid_semantic_registry(
    inventory: CircuitInventory,
    *,
    semantic_registry_dir: str | Path | None = None,
) -> tuple[SemanticRegistryBundle | None, Path, tuple[str, ...]]:
    path = semantic_registry_path_for_inventory(
        inventory,
        semantic_registry_dir=semantic_registry_dir,
    )

    if not path.exists():
        return None, path, ("semantic_registry_missing",)

    try:
        bundle = read_semantic_registry_bundle(path)
    except SemanticRegistryInvalidError as exc:
        return None, path, (f"semantic_registry_invalid: {exc}",)

    valid, reasons = validate_bundle_for_inventory(bundle, inventory)
    if not valid:
        return None, path, reasons

    return bundle, path, ()
