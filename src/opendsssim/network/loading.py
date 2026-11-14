"""Circuit-source validation and conservative source-tree identity."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Iterable

_SOURCE_EXCLUDED_PARTS = {
    ".git",
    ".opendsssim",
    ".pytest_cache",
    "__pycache__",
}


@dataclass(frozen=True)
class CircuitSourceDependency:
    """One file participating in the conservative circuit-source identity."""

    relative_path: str
    bytes: int
    sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "relative_path": self.relative_path,
            "bytes": self.bytes,
            "sha256": self.sha256,
        }


def _iter_source_files(source_root: Path) -> Iterable[Path]:
    """Yield every regular source-root file except explicit generated/cache trees.

    A02H1 intentionally uses a conservative source-tree identity. This can
    over-invalidate an inventory when an unrelated file changes, but it avoids
    silently reusing stale discovery when DSS/CSV/data dependencies change.
    """

    for path in sorted(
        source_root.rglob("*"),
        key=lambda item: item.relative_to(source_root).as_posix().casefold(),
    ):
        if not path.is_file():
            continue
        relative = path.relative_to(source_root)
        if any(part in _SOURCE_EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.suffix.lower() == ".pyc":
            continue
        yield path


def _compute_source_tree(
    source_root: Path,
) -> tuple[tuple[CircuitSourceDependency, ...], str]:
    dependencies: list[CircuitSourceDependency] = []
    h = sha256()

    for path in _iter_source_files(source_root):
        relative = path.relative_to(source_root).as_posix()
        data = path.read_bytes()
        digest = sha256(data).hexdigest().upper()

        dependency = CircuitSourceDependency(
            relative_path=relative,
            bytes=len(data),
            sha256=digest,
        )
        dependencies.append(dependency)

        h.update(relative.encode("utf-8"))
        h.update(b"\0")
        h.update(str(len(data)).encode("ascii"))
        h.update(b"\0")
        h.update(digest.encode("ascii"))
        h.update(b"\n")

    return tuple(dependencies), h.hexdigest().upper()


@dataclass(frozen=True)
class CircuitSource:
    """Immutable reference to one DSS master and its authoritative source tree.

    `sha256` is retained for A01/A02 compatibility and is the master-file hash.
    `source_tree_sha256` is the A02H1 identity used for persistent inventory
    invalidation.
    """

    master_path: Path
    sha256: str
    source_root: Path
    master_relative_path: str
    dependencies: tuple[CircuitSourceDependency, ...]
    source_tree_sha256: str

    @classmethod
    def from_path(
        cls,
        master_path: str | Path,
        *,
        source_root: str | Path | None = None,
    ) -> "CircuitSource":
        path = Path(master_path).expanduser().resolve()
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"DSS master file not found: {path}")
        if path.suffix.lower() != ".dss":
            raise ValueError(f"Expected a .dss master file: {path}")

        root = (
            Path(source_root).expanduser().resolve()
            if source_root is not None
            else path.parent
        )
        if not root.exists() or not root.is_dir():
            raise NotADirectoryError(f"Circuit source root not found: {root}")

        try:
            master_relative = path.relative_to(root).as_posix()
        except ValueError as exc:
            raise ValueError(
                "DSS master file must be contained within source_root. "
                f"master={path} source_root={root}"
            ) from exc

        master_digest = sha256(path.read_bytes()).hexdigest().upper()
        dependencies, source_tree_digest = _compute_source_tree(root)

        dependency_paths = {item.relative_path.casefold() for item in dependencies}
        if master_relative.casefold() not in dependency_paths:
            raise RuntimeError(
                "Master DSS file was unexpectedly excluded from source identity: "
                f"{master_relative}"
            )

        return cls(
            master_path=path,
            sha256=master_digest,
            source_root=root,
            master_relative_path=master_relative,
            dependencies=dependencies,
            source_tree_sha256=source_tree_digest,
        )

    @property
    def dependency_count(self) -> int:
        return len(self.dependencies)

    def validate(self) -> None:
        if not self.master_path.exists() or not self.master_path.is_file():
            raise FileNotFoundError(f"DSS master file not found: {self.master_path}")

        current_master = sha256(self.master_path.read_bytes()).hexdigest().upper()
        if current_master != self.sha256:
            raise RuntimeError(
                "DSS master file changed after CircuitSource creation: "
                f"{self.master_path}"
            )

        current_dependencies, current_tree = _compute_source_tree(self.source_root)
        if current_tree != self.source_tree_sha256:
            raise RuntimeError(
                "Circuit source tree changed after CircuitSource creation: "
                f"{self.source_root}"
            )

        if current_dependencies != self.dependencies:
            raise RuntimeError(
                "Circuit source dependency manifest changed after CircuitSource "
                f"creation: {self.source_root}"
            )


@dataclass(frozen=True)
class CircuitIdentity:
    """Minimal loaded-circuit identity used by A01+."""

    source: CircuitSource
    circuit_name: str
    num_buses: int
    num_nodes: int
    num_circuit_elements: int
