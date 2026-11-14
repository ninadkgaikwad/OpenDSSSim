"""Persistent A04I3 runtime-preflight qualification cache."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import re
import tempfile
from importlib.metadata import PackageNotFoundError, version as package_version
from typing import Any, Mapping

from opendsssim.persistence.inventory_schema import CircuitInventory
from opendsssim.problem.spaces import CompiledGymSpaces
from opendsssim.runtime.schema import ProblemRuntimeBinding
from opendsssim.semantics.schema import SemanticRegistryBundle

PREFLIGHT_SCHEMA_VERSION = "A04.runtime-preflight.v1"


def default_preflight_dir() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local).expanduser().resolve() / "OpenDSSSim" / "runtime_preflight"
    return Path.home().expanduser().resolve() / ".opendssim" / "runtime_preflight"


def _canonical(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True)
class A04RuntimePreflightRecord:
    schema_version: str
    status: str
    implementation_source_sha256: str
    backend: str
    altdss_version: str
    engine_version: str
    python_version: str
    gymnasium_version: str
    opendsssim_version: str
    inventory_semantic_sha256: str
    semantic_bundle_sha256: str
    resolved_problem_sha256: str
    observation_space_sha256: str
    action_space_sha256: str
    gym_space_contract_sha256: str
    runtime_binding_sha256: str
    hook_identities: tuple[str, ...]

    def identity_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "implementation_source_sha256": self.implementation_source_sha256,
            "backend": self.backend,
            "altdss_version": self.altdss_version,
            "engine_version": self.engine_version,
            "python_version": self.python_version,
            "gymnasium_version": self.gymnasium_version,
            "opendsssim_version": self.opendsssim_version,
            "inventory_semantic_sha256": self.inventory_semantic_sha256,
            "semantic_bundle_sha256": self.semantic_bundle_sha256,
            "resolved_problem_sha256": self.resolved_problem_sha256,
            "observation_space_sha256": self.observation_space_sha256,
            "action_space_sha256": self.action_space_sha256,
            "gym_space_contract_sha256": self.gym_space_contract_sha256,
            "runtime_binding_sha256": self.runtime_binding_sha256,
            "hook_identities": list(self.hook_identities),
        }

    @property
    def identity_sha256(self) -> str:
        return sha256(_canonical(self.identity_dict()).encode("utf-8")).hexdigest().upper()

    def to_dict(self) -> dict[str, Any]:
        payload = self.identity_dict()
        payload["status"] = self.status
        payload["identity_sha256"] = self.identity_sha256
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "A04RuntimePreflightRecord":
        record = cls(
            schema_version=str(payload["schema_version"]),
            status=str(payload["status"]),
            implementation_source_sha256=str(payload["implementation_source_sha256"]),
            backend=str(payload["backend"]),
            altdss_version=str(payload["altdss_version"]),
            engine_version=str(payload["engine_version"]),
            python_version=str(payload["python_version"]),
            gymnasium_version=str(payload["gymnasium_version"]),
            opendsssim_version=str(payload["opendsssim_version"]),
            inventory_semantic_sha256=str(payload["inventory_semantic_sha256"]),
            semantic_bundle_sha256=str(payload["semantic_bundle_sha256"]),
            resolved_problem_sha256=str(payload["resolved_problem_sha256"]),
            observation_space_sha256=str(payload["observation_space_sha256"]),
            action_space_sha256=str(payload["action_space_sha256"]),
            gym_space_contract_sha256=str(payload["gym_space_contract_sha256"]),
            runtime_binding_sha256=str(payload["runtime_binding_sha256"]),
            hook_identities=tuple(str(v) for v in payload.get("hook_identities", [])),
        )
        if payload.get("identity_sha256") != record.identity_sha256:
            raise ValueError("A04 runtime-preflight identity hash mismatch.")
        return record


def _dist_version(name: str) -> str:
    try:
        return package_version(name)
    except PackageNotFoundError:
        return "unknown"


def _opendsssim_version() -> str:
    installed = _dist_version("opendsssim")
    if installed != "unknown":
        return installed
    pyproject = Path(__file__).resolve().parents[3] / "pyproject.toml"
    try:
        text = pyproject.read_text(encoding="utf-8")
    except OSError:
        return "unknown"
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, flags=re.MULTILINE)
    return "unknown" if match is None else match.group(1)


def make_preflight_record(binding: ProblemRuntimeBinding, spaces: CompiledGymSpaces, inventory: CircuitInventory, bundle: SemanticRegistryBundle) -> A04RuntimePreflightRecord:
    return A04RuntimePreflightRecord(
        schema_version=PREFLIGHT_SCHEMA_VERSION,
        status="PASS",
        implementation_source_sha256=binding.implementation_source_sha256,
        backend=inventory.backend,
        altdss_version=inventory.altdss_version,
        engine_version=inventory.engine_version,
        python_version=platform.python_version(),
        gymnasium_version=_dist_version("gymnasium"),
        opendsssim_version=_opendsssim_version(),
        inventory_semantic_sha256=inventory.semantic_sha256,
        semantic_bundle_sha256=bundle.semantic_sha256,
        resolved_problem_sha256=binding.resolved_problem.resolved_problem_sha256,
        observation_space_sha256=spaces.observation_space_sha256,
        action_space_sha256=spaces.action_space_sha256,
        gym_space_contract_sha256=spaces.gym_space_contract_sha256,
        runtime_binding_sha256=binding.runtime_binding_sha256,
        hook_identities=(binding.reward_hook.identity, binding.termination_hook.identity, binding.truncation_hook.identity),
    )


def preflight_path(record: A04RuntimePreflightRecord, root: str | Path | None = None) -> Path:
    base = Path(root).expanduser().resolve() if root is not None else default_preflight_dir()
    stem = binding_stem(record.resolved_problem_sha256)
    return base / f"{stem}__{record.identity_sha256[:24]}.json"


def binding_stem(value: str) -> str:
    return "problem_" + value[:16]


def write_preflight(path: str | Path, record: A04RuntimePreflightRecord) -> Path:
    path = Path(path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(record.to_dict(), handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp, path)
    except Exception:
        try: os.unlink(tmp)
        except FileNotFoundError: pass
        raise
    return path


def ensure_preflight(record: A04RuntimePreflightRecord, root: str | Path | None = None) -> tuple[str, Path]:
    path = preflight_path(record, root)
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            existing = A04RuntimePreflightRecord.from_dict(payload)
            if existing.status == "PASS" and existing.identity_sha256 == record.identity_sha256:
                return "REUSED", path
        except Exception:
            pass
    write_preflight(path, record)
    return "BUILT", path
