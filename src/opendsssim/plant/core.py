"""Plant orchestration through A03 persistent semantic registries."""

from __future__ import annotations

from pathlib import Path

from opendsssim.backends.base import DistributionBackend
from opendsssim.discovery.schema import CircuitDiscovery, EngineDiscovery
from opendsssim.network.loading import CircuitIdentity, CircuitSource
from opendsssim.persistence.inventory import (
    build_circuit_inventory,
    load_valid_inventory,
    write_circuit_inventory,
)
from opendsssim.persistence.inventory_schema import CircuitInventory
from opendsssim.persistence.semantic_registry import (
    load_valid_semantic_registry,
    semantic_registry_path_for_inventory,
    write_semantic_registry_bundle,
)
from opendsssim.plant.solution import SolutionResult
from opendsssim.semantics.compiler import compile_semantic_registry_bundle
from opendsssim.semantics.schema import SemanticRegistryBundle


class OpenDSSPlant:
    """Own backend/source plus persistent physical and semantic inventories."""

    def __init__(
        self,
        backend: DistributionBackend,
        source: CircuitSource,
        *,
        inventory_dir: str | Path | None = None,
        semantic_registry_dir: str | Path | None = None,
    ) -> None:
        self._backend = backend
        self._source = source
        self._identity: CircuitIdentity | None = None
        self._closed = False
        self._inventory_dir = inventory_dir
        self._inventory_build_count = 0

        inventory, path, reasons = load_valid_inventory(
            source,
            backend="altdss",
            altdss_version=getattr(backend, "altdss_package_version", "unknown"),
            engine_version=backend.engine_version,
            inventory_dir=inventory_dir,
        )
        self._inventory = inventory
        self._inventory_path = path
        self._inventory_invalid_reasons = reasons
        self._inventory_status = "LOADED" if inventory is not None else "MISSING"

        if semantic_registry_dir is not None:
            self._semantic_registry_dir = semantic_registry_dir
        elif inventory_dir is not None:
            self._semantic_registry_dir = Path(inventory_dir) / "semantic_registry"
        else:
            self._semantic_registry_dir = None

        self._semantic_registry: SemanticRegistryBundle | None = None
        self._semantic_registry_path: Path | None = None
        self._semantic_registry_invalid_reasons: tuple[str, ...] = ()
        self._semantic_registry_status = "WAITING_FOR_INVENTORY"
        self._semantic_registry_compile_count = 0

        if inventory is not None:
            self._load_semantic_registry(inventory)

    @property
    def backend(self) -> DistributionBackend:
        return self._backend

    @property
    def circuit_identity(self) -> CircuitIdentity | None:
        return self._identity

    @property
    def context_identity(self) -> int:
        return self._backend.context_identity

    @property
    def circuit_inventory(self) -> CircuitInventory | None:
        return self._inventory

    @property
    def inventory_path(self) -> Path:
        return self._inventory_path

    @property
    def inventory_status(self) -> str:
        return self._inventory_status

    @property
    def inventory_build_count(self) -> int:
        return self._inventory_build_count

    @property
    def inventory_invalid_reasons(self) -> tuple[str, ...]:
        return self._inventory_invalid_reasons

    @property
    def semantic_registry(self) -> SemanticRegistryBundle | None:
        return self._semantic_registry

    @property
    def semantic_registry_path(self) -> Path | None:
        return self._semantic_registry_path

    @property
    def semantic_registry_status(self) -> str:
        return self._semantic_registry_status

    @property
    def semantic_registry_compile_count(self) -> int:
        return self._semantic_registry_compile_count

    @property
    def semantic_registry_invalid_reasons(self) -> tuple[str, ...]:
        return self._semantic_registry_invalid_reasons

    def _load_semantic_registry(self, inventory: CircuitInventory) -> None:
        bundle, path, reasons = load_valid_semantic_registry(
            inventory,
            semantic_registry_dir=self._semantic_registry_dir,
        )
        self._semantic_registry = bundle
        self._semantic_registry_path = path
        self._semantic_registry_invalid_reasons = reasons
        if bundle is not None:
            self._semantic_registry_status = "LOADED"
        elif reasons and any(
            not reason.startswith("semantic_registry_missing")
            for reason in reasons
        ):
            self._semantic_registry_status = "INVALID"
        else:
            self._semantic_registry_status = "MISSING"

    def _ensure_inventory(self) -> CircuitInventory:
        if self._inventory is not None:
            self._inventory_status = "REUSED"
            return self._inventory

        discovery = self._backend.discover_circuit()
        inventory = build_circuit_inventory(
            discovery,
            self._source,
            backend="altdss",
        )
        write_circuit_inventory(self._inventory_path, inventory)

        self._inventory = inventory
        self._inventory_build_count += 1
        self._inventory_status = "BUILT"
        self._inventory_invalid_reasons = ()
        self._load_semantic_registry(inventory)
        return inventory

    def _ensure_semantic_registry(
        self,
        inventory: CircuitInventory,
    ) -> SemanticRegistryBundle:
        if self._semantic_registry is not None:
            self._semantic_registry_status = "REUSED"
            return self._semantic_registry

        if self._semantic_registry_path is None:
            self._semantic_registry_path = semantic_registry_path_for_inventory(
                inventory,
                semantic_registry_dir=self._semantic_registry_dir,
            )

        bundle = compile_semantic_registry_bundle(inventory, self._backend)
        write_semantic_registry_bundle(self._semantic_registry_path, bundle)

        self._semantic_registry = bundle
        self._semantic_registry_compile_count += 1
        self._semantic_registry_status = "BUILT"
        self._semantic_registry_invalid_reasons = ()
        return bundle

    def prepare_reset(self) -> CircuitIdentity:
        """Compile/restore the baseline without solving, then ensure static A03 authority.

        A04I3 uses this once before episode configuration so control authority and
        static faults can be established before the first authoritative solve.
        """
        if self._closed:
            raise RuntimeError("OpenDSSPlant is closed.")
        self._identity = self._backend.load_circuit(self._source)
        inventory = self._ensure_inventory()
        self._ensure_semantic_registry(inventory)
        return self._identity

    def reset(self) -> SolutionResult:
        if self._closed:
            raise RuntimeError("OpenDSSPlant is closed.")

        self._identity = self._backend.load_circuit(self._source)
        result = self._backend.solve_snapshot()
        inventory = self._ensure_inventory()
        self._ensure_semantic_registry(inventory)
        return result

    def solve_snapshot(self) -> SolutionResult:
        if self._closed:
            raise RuntimeError("OpenDSSPlant is closed.")
        if self._identity is None:
            self._identity = self._backend.load_circuit(self._source)
        return self._backend.solve_snapshot()

    def discover_engine(self) -> EngineDiscovery:
        if self._closed:
            raise RuntimeError("OpenDSSPlant is closed.")
        return self._backend.discover_engine()

    def discover_circuit(self) -> CircuitDiscovery:
        if self._closed:
            raise RuntimeError("OpenDSSPlant is closed.")
        return self._backend.discover_circuit()

    def close(self) -> None:
        if self._closed:
            return
        self._backend.close()
        self._closed = True
