"""Gymnasium plant boundary through A04I3 runtime binding and history."""
from __future__ import annotations

from copy import deepcopy
from numbers import Real
from pathlib import Path
from typing import Any, Mapping

import gymnasium as gym
from gymnasium import spaces
import numpy as np

from opendsssim.backends.base import OpenDSSSimBackendError
from opendsssim.backends.factory import create_backend
from opendsssim.discovery.schema import CircuitDiscovery, EngineDiscovery
from opendsssim.network.loading import CircuitSource
from opendsssim.persistence.inventory_schema import CircuitInventory
from opendsssim.persistence.preflight import ensure_preflight, make_preflight_record
from opendsssim.plant.core import OpenDSSPlant
from opendsssim.plant.solution import SolutionResult
from opendsssim.problem import ProblemSpec, ResolvedProblemSpec, compile_gym_spaces, resolve_problem
from opendsssim.problem.spaces import CompiledGymSpaces, SpaceLayoutEntry
from opendsssim.runtime import (
    ActionApplicationStatus,
    ActionChannelAudit,
    ExecutionProfile,
    HistoryLevel,
    ProblemRuntimeBinding,
    RuntimeHistory,
    RuntimeStepContext,
    SemanticRuntimeAccess,
    build_runtime_binding,
)
from opendsssim.semantics.schema import (
    NativePropertyAddress,
    RuntimeCommandAddress,
    RuntimeReadoutAddress,
    SemanticEntry,
    SemanticRegistryBundle,
)

from .exogenous import ExogenousApplicationError, ExogenousProfileSpec, PhysicalExogenousBinding
from .replay import ReplaySpec, ReplaySession, ReplayValidationError
from .forecast import ExogenousForecastOracle, ForecastResult, ForecastError
from .uncertainty import ForecastNoiseSpec, ForecastNoiseEngine, TrustedPrimitiveAudit
from .controller_context import (ControllerContext, ControllerInformationError,
                                 ControllerContextUnavailable, build_controller_context)

from .clock import (
    EpisodeClock,
    EpisodeClockError,
    EpisodeSpec,
    TemporalRuntimeHistory,
    TemporalRuntimeStepContext,
)


class RuntimeActionError(RuntimeError):
    pass


class RuntimeObservationError(RuntimeError):
    pass


class RuntimeHookError(RuntimeError):
    pass


def _nested_get(mapping: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = mapping
    for part in path:
        if not isinstance(value, Mapping) or part not in value:
            raise RuntimeActionError(f"Canonical action path is missing: {'/'.join(path)}")
        value = value[part]
    return value


def _nested_set(mapping: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    node = mapping
    for part in path[:-1]:
        child = node.get(part)
        if child is None:
            child = {}
            node[part] = child
        if not isinstance(child, dict):
            raise RuntimeError(f"Canonical semantic path collision: {'/'.join(path)}")
        node = child
    node[path[-1]] = value


def _plain(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_plain(v) for v in value]
    if isinstance(value, list):
        return [_plain(v) for v in value]
    if isinstance(value, complex):
        return [float(value.real), float(value.imag)]
    return value


def _finite(value: Any) -> bool:
    if isinstance(value, (str, bool, np.bool_)):
        return True
    if isinstance(value, Real) or isinstance(value, np.number):
        return bool(np.isfinite(value))
    if isinstance(value, np.ndarray):
        return bool(np.all(np.isfinite(value))) if np.issubdtype(value.dtype, np.number) else True
    if isinstance(value, Mapping):
        return all(_finite(v) for v in value.values())
    if isinstance(value, (tuple, list)):
        return all(_finite(v) for v in value)
    return True


def _encode_observation(raw: Any, layout: SpaceLayoutEntry) -> Any:
    shape = tuple(layout.shape)
    if layout.component_order == ("real", "imag"):
        arr = np.asarray(raw, dtype=np.complex128)
        encoded = np.stack((arr.real, arr.imag), axis=-1).astype(np.float64, copy=False)
        if tuple(encoded.shape) != shape:
            raise RuntimeObservationError(
                f"Complex semantic {layout.semantic_id} resolved shape {encoded.shape} != {shape}."
            )
        return encoded
    if layout.space_type == "Box":
        arr = np.asarray(raw, dtype=np.float64)
        if tuple(arr.shape) != shape:
            raise RuntimeObservationError(
                f"Semantic {layout.semantic_id} resolved shape {arr.shape} != {shape}."
            )
        return arr
    if layout.space_type == "MultiBinary":
        arr = np.asarray(raw, dtype=np.int8)
        if tuple(arr.shape) != shape:
            raise RuntimeObservationError(
                f"Semantic {layout.semantic_id} resolved shape {arr.shape} != {shape}."
            )
        return arr
    if layout.space_type == "Discrete":
        return int(bool(raw)) if layout.domain_values == (0, 1) else int(raw)
    if layout.space_type == "MultiDiscrete":
        return np.asarray(raw, dtype=np.int64)
    raise RuntimeObservationError(f"Unsupported observation space type: {layout.space_type}")


def _decode_action(raw: Any, layout: SpaceLayoutEntry) -> Any:
    if layout.space_type == "Box":
        arr = np.asarray(raw, dtype=np.float64)
        return float(arr) if arr.shape == () else arr.tolist()
    if layout.space_type == "Discrete":
        value = int(raw)
        if layout.domain_values and any(isinstance(item, str) for item in layout.domain_values):
            if value < 0 or value >= len(layout.domain_values):
                raise RuntimeActionError(f"Categorical action index out of range for {layout.semantic_id}.")
            return layout.domain_values[value]
        return value
    if layout.space_type in {"MultiBinary", "MultiDiscrete"}:
        return np.asarray(raw).tolist()
    return _plain(raw)


class OpenDSSSimulator(gym.Env):
    """Generalized Gymnasium plant through A04I3 runtime integration."""

    metadata = {"render_modes": []}

    def __init__(
        self,
        network: str | Path,
        backend: str = "altdss",
        *,
        source_root: str | Path | None = None,
        inventory_dir: str | Path | None = None,
        semantic_registry_dir: str | Path | None = None,
        problem: ProblemSpec | None = None,
        history_level: HistoryLevel | str = HistoryLevel.H1,
        execution_profile: ExecutionProfile | str = ExecutionProfile.STANDARD,
        preflight_dir: str | Path | None = None,
        episode_spec: EpisodeSpec | None = None,
        exogenous: ExogenousProfileSpec | None = None,
        exogenous_replay: ReplaySpec | None = None,
        forecast_noise: ForecastNoiseSpec | None = None,
    ) -> None:
        super().__init__()
        source = CircuitSource.from_path(network, source_root=source_root)
        backend_obj = create_backend(backend)
        self._plant = OpenDSSPlant(
            backend_obj,
            source,
            inventory_dir=inventory_dir,
            semantic_registry_dir=semantic_registry_dir,
        )
        self._problem_spec = problem
        self._resolved_problem: ResolvedProblemSpec | None = None
        self._compiled_spaces: CompiledGymSpaces | None = None
        self._binding: ProblemRuntimeBinding | None = None
        self._access = SemanticRuntimeAccess(self._plant.backend)
        self._preflight_dir = preflight_dir
        self._preflight_status = "NOT_APPLICABLE"
        self._preflight_path: Path | None = None
        self.history = TemporalRuntimeHistory(HistoryLevel(history_level), ExecutionProfile(execution_profile))
        self._closed = False
        self._last_result: SolutionResult | None = None
        self._current_context: RuntimeStepContext | None = None
        self._step_index = 0
        self._episode_active = False
        self._initial_problem_context_prepared = False
        if episode_spec is not None and not isinstance(episode_spec, EpisodeSpec):
            raise TypeError("episode_spec must be an EpisodeSpec or None")
        self._episode_spec = episode_spec or EpisodeSpec()
        self._episode_clock: EpisodeClock | None = None
        self._episode_number = 0
        if exogenous is not None and not isinstance(exogenous, ExogenousProfileSpec):
            raise TypeError("exogenous must be an ExogenousProfileSpec or None")
        if exogenous_replay is not None:
            if not isinstance(exogenous_replay, ReplaySpec):
                raise TypeError("exogenous_replay must be a ReplaySpec")
            if exogenous is not None or episode_spec is not None:
                raise ValueError("A05I3 replay owns episode time and physical truth: do not also supply episode_spec or exogenous")
        self._replay_spec = exogenous_replay
        self._replay_session: ReplaySession | None = None
        self._exogenous_spec = exogenous
        self._exogenous_binding: PhysicalExogenousBinding | None = None
        self._exogenous_last_audit: dict[str, Any] | None = None
        if forecast_noise is not None and not isinstance(forecast_noise, ForecastNoiseSpec):
            raise TypeError("forecast_noise must be a ForecastNoiseSpec or None")
        self._forecast_noise = forecast_noise or ForecastNoiseSpec()
        self._forecast_private_audit: tuple[TrustedPrimitiveAudit, ...] = ()

        self.action_space = spaces.Dict({})
        self.observation_space = spaces.Dict({"converged": spaces.Discrete(2)})

        # A problem-aware Gym consumer must be able to inspect spaces before reset.
        # Compile the feeder/A03 authority once here, but do not write actuators or solve.
        if problem is not None:
            self._plant.prepare_reset()
            self._compile_problem_contract()
            self._initial_problem_context_prepared = True

    @property
    def context_identity(self) -> int:
        return self._plant.context_identity

    @property
    def last_result(self) -> SolutionResult | None:
        return self._last_result

    @property
    def state(self) -> RuntimeStepContext | None:
        return self._current_context

    @property
    def episode_clock(self) -> EpisodeClock | None:
        """Immutable external clock, never a mutable backend handle."""
        return self._episode_clock

    def exogenous_forecast(self, horizon: int, *, channel_ids=None, entity_ids=None,
                           required: bool = True) -> ForecastResult:
        """A05I4 authorized, read-only perfect-exogenous forecast oracle.

        Only qualified user-declared exogenous signals are returned. The
        forecast is anchored to the *next decision clock*, not the latest
        electrical sample. It never writes, solves, or advances a clock.
        """
        if self._closed or not self._episode_active or self._episode_clock is None:
            raise ForecastError("A05I4_REQUIRES_ACTIVE_EPISODE")
        oracle = ExogenousForecastOracle(
            clock=self._episode_clock,
            replay_session=self._replay_session,
            replay_spec=self._replay_spec,
            explicit_source=None if self._replay_session is not None else self._exogenous_spec,
        )
        if self._forecast_noise.mode == "none":
            self._forecast_private_audit = ()
            return oracle.request(self._step_index, horizon,
                                  channel_ids=channel_ids, entity_ids=entity_ids,
                                  required=required)
        # Request the entire qualified physical group before deriving noisy
        # dependent quantities, then project only the requested public subset.
        unperturbed = oracle.request(self._step_index, horizon, required=required)
        if unperturbed.status != "AVAILABLE":
            self._forecast_private_audit = ()
            return unperturbed
        noise = ForecastNoiseEngine(self._forecast_noise,
                                   replay_spec=self._replay_spec,
                                   explicit_source=None if self._replay_session is not None else self._exogenous_spec,
                                   reset_seed=self._episode_clock.reset_seed)
        noisy, private_audit = noise.transform(unperturbed,
                                              channel_ids=channel_ids,
                                              entity_ids=entity_ids)
        # The private audit is deliberately excluded from Gym/step info and
        # the public result; A05I6 will establish trusted persistence routing.
        self._forecast_private_audit = private_audit
        return noisy

    def controller_context(self, *, forecast_horizon: int | None = None,
                           channel_ids=None, entity_ids=None,
                           required: bool = False, device_entities=None,
                           include_static_network: bool = True) -> ControllerContext:
        """Official A05I6 read-only decision-time view for a controlled client.

        Forecast selectors inherit A05I4/A05I5 qualification. Only A04-selected
        device identities may be requested for live enabledness readback.
        No backend handles, hidden truth tables, private noise draws or history
        are returned. Canonical Gym observation and action shapes do not change.
        """
        if (self._closed or not self._episode_active or
                self._episode_clock is None or self._current_context is None):
            raise ControllerContextUnavailable('A05I6_REQUIRES_ACTIVE_COMMITTED_EPISODE')
        if forecast_horizon is None:
            if channel_ids is not None or entity_ids is not None:
                raise ControllerInformationError('FORECAST_SELECTORS_REQUIRE_HORIZON')
            forecast = None
        else:
            forecast = self.exogenous_forecast(
                forecast_horizon, channel_ids=channel_ids,
                entity_ids=entity_ids, required=required)
        return build_controller_context(
            clock=self._episode_clock, completed_steps=self._step_index,
            observation=self._current_context.observation,
            compiled_spaces=self._compiled_spaces, runtime_binding=self._binding,
            inventory=self._plant.circuit_inventory, access=self._access,
            action_audits=tuple(self._current_context.action_audit), forecast=forecast,
            device_entities=device_entities,
            include_static_network=include_static_network)

    @property
    def runtime_binding(self) -> ProblemRuntimeBinding | None:
        return self._binding

    @property
    def resolved_problem(self) -> ResolvedProblemSpec | None:
        return self._resolved_problem

    @property
    def preflight_status(self) -> str:
        return self._preflight_status

    @property
    def preflight_path(self) -> Path | None:
        return self._preflight_path

    @property
    def circuit_inventory(self) -> CircuitInventory | None:
        return self._plant.circuit_inventory

    @property
    def inventory_status(self) -> str:
        return self._plant.inventory_status

    @property
    def inventory_path(self) -> Path:
        return self._plant.inventory_path

    @property
    def inventory_build_count(self) -> int:
        return self._plant.inventory_build_count

    @property
    def inventory_invalid_reasons(self) -> tuple[str, ...]:
        return self._plant.inventory_invalid_reasons

    @property
    def semantic_registry(self) -> SemanticRegistryBundle | None:
        return self._plant.semantic_registry

    @property
    def semantic_registry_status(self) -> str:
        return self._plant.semantic_registry_status

    @property
    def semantic_registry_path(self) -> Path | None:
        return self._plant.semantic_registry_path

    @property
    def semantic_registry_compile_count(self) -> int:
        return self._plant.semantic_registry_compile_count

    @property
    def semantic_registry_invalid_reasons(self) -> tuple[str, ...]:
        return self._plant.semantic_registry_invalid_reasons

    def discover_engine(self) -> EngineDiscovery:
        if self._closed: raise RuntimeError("OpenDSSSimulator is closed.")
        return self._plant.discover_engine()

    def discover_circuit(self) -> CircuitDiscovery:
        if self._closed: raise RuntimeError("OpenDSSSimulator is closed.")
        return self._plant.discover_circuit()

    def _compile_problem_contract(self) -> None:
        inventory = self._plant.circuit_inventory
        bundle = self._plant.semantic_registry
        if inventory is None or bundle is None or self._problem_spec is None:
            raise RuntimeError("Problem runtime compilation requires inventory, semantic registry, and ProblemSpec.")
        self._resolved_problem = resolve_problem(self._problem_spec, bundle, inventory)
        if self._resolved_problem is None:  # pragma: no cover
            raise RuntimeError("ProblemSpec unexpectedly resolved to None.")
        self._compiled_spaces = compile_gym_spaces(self._resolved_problem)
        self._binding = build_runtime_binding(
            self._resolved_problem, self._compiled_spaces, bundle, inventory, self._plant.backend
        )
        self.observation_space = self._compiled_spaces.observation_space
        self.action_space = self._compiled_spaces.action_space
        record = make_preflight_record(self._binding, self._compiled_spaces, inventory, bundle)
        self._preflight_status, self._preflight_path = ensure_preflight(record, self._preflight_dir)

    def _verify_binding_identity(self) -> None:
        if self._binding is None: return
        inv = self._plant.circuit_inventory; bundle = self._plant.semantic_registry
        if inv is None or bundle is None:
            raise RuntimeError("A04 runtime authority disappeared after reset preparation.")
        if inv.semantic_sha256 != self._binding.resolved_problem.source_inventory_semantic_sha256:
            raise RuntimeError("CircuitInventory identity changed after runtime binding.")
        if bundle.semantic_sha256 != self._binding.resolved_problem.source_semantic_bundle_sha256:
            raise RuntimeError("SemanticRegistryBundle identity changed after runtime binding.")

    def _prepare_exogenous(self) -> None:
        """Resolve one A05I2 truth writer after baseline restore, before first solve."""
        if self._exogenous_spec is None:
            self._exogenous_binding = None
            return
        inventory = self._plant.circuit_inventory
        semantics = self._plant.semantic_registry
        if inventory is None or semantics is None:
            raise RuntimeError("A05I2 physical binding requires qualified A03 inventory and semantics")
        actions = () if self._binding is None else tuple(
            b.entry.address for b in self._binding.action_bindings
            if isinstance(b.entry.address, NativePropertyAddress)
        )
        self._exogenous_binding = PhysicalExogenousBinding(
            self._exogenous_spec, inventory, semantics, self._access, actions
        )

    def _apply_exogenous(self, index: int, time: dict[str, Any]) -> dict[str, Any] | None:
        if self._exogenous_binding is None:
            return None
        if self._replay_session is not None:
            physical, provenance = self._replay_session.sample(index)
            # The A05I2 authority and baseline are bound once per reset. Swap
            # only its validated one-row *truth*, not inventory or native access.
            self._exogenous_binding.spec = physical
            self._exogenous_last_audit = self._exogenous_binding.apply(0)
            self._exogenous_last_audit["replay"] = provenance
            time["exogenous_sample_status"] = "A05I3_FILE_REPLAY_APPLIED"
            time["replay"] = provenance
            public = self._exogenous_binding.public_provenance(0)
            public["replay"] = provenance
            return public
        self._exogenous_last_audit = self._exogenous_binding.apply(index)
        time["exogenous_sample_status"] = "A05I2_BOUND_EXPLICIT"
        return self._exogenous_binding.public_provenance(index)

    def _capture_exogenous_realized(self) -> None:
        if self._exogenous_binding is not None and self._exogenous_last_audit is not None:
            self._exogenous_binding.capture_realized(self._exogenous_last_audit)

    def _apply_static_configuration(self) -> None:
        assert self._binding is not None
        for controller in self._binding.disabled_native_controls:
            value = self._access.write(NativePropertyAddress(controller, "Enabled"), False)
            if bool(value):
                raise RuntimeError(f"Failed to suppress native controller {controller}.")
        for target in self._binding.fault_targets:
            value = self._access.write(NativePropertyAddress(target, "Enabled"), False)
            if bool(value):
                raise RuntimeError(f"Failed to apply static fault to {target}.")

    def _verify_static_configuration(self) -> None:
        assert self._binding is not None
        for name in self._binding.disabled_native_controls:
            if bool(self._access.read(NativePropertyAddress(name, "Enabled"))):
                raise RuntimeError(f"External authority lost: native controller re-enabled: {name}")
        for name in self._binding.fault_targets:
            if bool(self._access.read(NativePropertyAddress(name, "Enabled"))):
                raise RuntimeError(f"Static fault lost: device re-enabled: {name}")

    def _read_binding_values(self, bindings: tuple[Any, ...]) -> dict[str, Any]:
        return {binding.semantic_id: self._access.read(binding.entry.address) for binding in bindings}

    def _read_observation(self) -> tuple[dict[str, Any], dict[str, Any]]:
        assert self._binding is not None
        obs: dict[str, Any] = {}; raw_by_id: dict[str, Any] = {}
        for binding in self._binding.observation_bindings:
            raw = self._access.read(binding.entry.address)
            raw_by_id[binding.semantic_id] = raw
            assert binding.layout is not None
            _nested_set(obs, binding.path, _encode_observation(raw, binding.layout))
        if not self.observation_space.contains(obs):
            raise RuntimeObservationError("Constructed observation does not satisfy the compiled A04 Gym space.")
        return obs, raw_by_id

    def _read_full_state(self) -> dict[str, Any]:
        bundle = self._plant.semantic_registry
        if bundle is None: return {}
        entries = {entry.semantic_id: entry for entry in bundle.semantic_entries}
        result: dict[str, Any] = {}
        for semantic_id in bundle.state_registry.entry_ids:
            entry = entries[semantic_id]
            try:
                result[semantic_id] = _plain(self._access.read(entry.address))
            except Exception as exc:
                result[semantic_id] = {"unavailable": type(exc).__name__, "message": str(exc)}
        return result

    def _decode_and_apply_actions(self, action: dict[str, Any]) -> tuple[dict[str, Any], tuple[ActionChannelAudit, ...]]:
        assert self._binding is not None
        applied: dict[str, Any] = {}
        audits: list[ActionChannelAudit] = []
        faulted = {name.casefold() for name in self._binding.fault_targets}
        external = {name.casefold() for name in self._binding.resolved_problem.control_authority.external_entities}

        # Validate all semantic values before the first backend write.
        prepared: list[tuple[Any, Any, Any]] = []
        for binding in self._binding.action_bindings:
            assert binding.layout is not None
            requested = _nested_get(action, binding.path)
            if not _finite(requested):
                raise RuntimeActionError(f"NONFINITE_ACTION for {binding.semantic_id}")
            prepared.append((binding, requested, _decode_action(requested, binding.layout)))

        for binding, requested, native_value in prepared:
            entity = binding.entry.native_entity
            requested_plain = _plain(requested)
            if entity is not None and entity.casefold() in faulted:
                audits.append(
                    ActionChannelAudit(
                        binding.semantic_id,
                        entity,
                        ActionApplicationStatus.FAULT_DISABLED,
                        requested_plain,
                        detail="static fault lockout",
                    )
                )
                continue
            if entity is None or entity.casefold() not in external:
                audits.append(
                    ActionChannelAudit(
                        binding.semantic_id,
                        entity,
                        ActionApplicationStatus.AUTHORITY_NATIVE,
                        requested_plain,
                        detail="not externally owned",
                    )
                )
                continue
            try:
                self._access.write(binding.entry.address, native_value)
            except Exception as exc:
                audits.append(
                    ActionChannelAudit(
                        binding.semantic_id,
                        entity,
                        ActionApplicationStatus.BACKEND_APPLICATION_ERROR,
                        requested_plain,
                        detail=str(exc),
                    )
                )
                raise RuntimeActionError(
                    f"Backend action application failed for {binding.semantic_id}"
                ) from exc
            _nested_set(applied, binding.path, deepcopy(requested))
            audits.append(
                ActionChannelAudit(
                    binding.semantic_id,
                    entity,
                    ActionApplicationStatus.ADMISSIBLE_APPLIED,
                    requested_plain,
                    requested_plain,
                    None,
                )
            )
        return applied, tuple(audits)

    def _read_realized_action_value(self, binding: Any) -> Any:
        address = binding.entry.address
        if isinstance(address, NativePropertyAddress):
            return self._access.read(address)
        if isinstance(address, RuntimeCommandAddress):
            service = address.service.casefold()
            operation = address.operation.casefold()
            if service in {"transformer", "autotrans"} and operation == "set_tap":
                return self._access.read(
                    RuntimeReadoutAddress(address.service, address.entity, "taps")
                )
            if service == "circuitelement" and operation == "open_close":
                return self._access.read(
                    RuntimeReadoutAddress("CircuitElement", address.entity, "open_state")
                )
            if service == "load" and operation == "set_served_fraction":
                return self._access.read(
                    RuntimeReadoutAddress("Load", address.entity, "applied_fraction")
                )
        raise RuntimeActionError(
            f"No qualified realized-state readout exists for applied action {binding.semantic_id}."
        )

    def _finalize_realized_actions(
        self,
        audits: tuple[ActionChannelAudit, ...],
    ) -> tuple[dict[str, Any], tuple[ActionChannelAudit, ...]]:
        assert self._binding is not None
        binding_by_id = {binding.semantic_id: binding for binding in self._binding.action_bindings}
        realized: dict[str, Any] = {}
        finalized: list[ActionChannelAudit] = []

        for audit in audits:
            if audit.status is not ActionApplicationStatus.ADMISSIBLE_APPLIED:
                finalized.append(audit)
                continue

            binding = binding_by_id[audit.semantic_id]
            try:
                realized_value = self._read_realized_action_value(binding)
            except Exception as exc:
                raise RuntimeActionError(
                    f"Post-solve realized-state read failed for {audit.semantic_id}"
                ) from exc

            realized_plain = _plain(realized_value)
            _nested_set(realized, binding.path, realized_plain)
            finalized.append(
                ActionChannelAudit(
                    semantic_id=audit.semantic_id,
                    native_entity=audit.native_entity,
                    status=audit.status,
                    requested_value=audit.requested_value,
                    applied_value=audit.applied_value,
                    realized_value=realized_plain,
                    detail=audit.detail,
                )
            )

        return realized, tuple(finalized)

    def _availability(self) -> dict[str, Any]:
        if self._binding is None: return {}
        faulted = {name.casefold() for name in self._binding.fault_targets}
        entities = sorted({b.entry.native_entity for b in self._binding.action_bindings if b.entry.native_entity}, key=str.casefold)
        return {entity: entity.casefold() not in faulted for entity in entities}

    def _authority(self) -> dict[str, Any]:
        if self._binding is None: return {"mode": "NATIVE", "native_entities": [], "external_entities": []}
        auth = self._binding.resolved_problem.control_authority
        return {"mode": auth.mode.value, "native_entities": list(auth.native_entities), "external_entities": list(auth.external_entities), "disabled_native_controls": list(self._binding.disabled_native_controls)}

    def _invoke_hooks(self, context: RuntimeStepContext) -> tuple[float, bool, bool]:
        assert self._binding is not None
        try:
            reward_raw = self._binding.reward_hook.fn(context, **dict(self._binding.reward_hook.config))
            termination_raw = self._binding.termination_hook.fn(context, **dict(self._binding.termination_hook.config))
            truncation_raw = self._binding.truncation_hook.fn(context, **dict(self._binding.truncation_hook.config))
        except Exception as exc:
            raise RuntimeHookError("ProblemSpec runtime hook raised an exception.") from exc
        if isinstance(reward_raw, (bool, np.bool_)) or not isinstance(reward_raw, (Real, np.number)) or not np.isfinite(reward_raw):
            raise RuntimeHookError(f"Reward hook must return one finite scalar numeric value; got {reward_raw!r}.")
        if not isinstance(termination_raw, (bool, np.bool_)):
            raise RuntimeHookError(f"Termination hook must return bool; got {termination_raw!r}.")
        if not isinstance(truncation_raw, (bool, np.bool_)):
            raise RuntimeHookError(f"Truncation hook must return bool; got {truncation_raw!r}.")
        return float(reward_raw), bool(termination_raw), bool(truncation_raw)

    def _base_info(self, result: SolutionResult) -> dict[str, Any]:
        inventory = self._plant.circuit_inventory; semantic_registry = self._plant.semantic_registry
        return {
            "solution": result.to_dict(),
            "inventory": {"status": self._plant.inventory_status, "path": str(self._plant.inventory_path), "semantic_sha256": None if inventory is None else inventory.semantic_sha256, "build_count": self._plant.inventory_build_count},
            "semantic_registry": {"status": self._plant.semantic_registry_status, "path": None if self._plant.semantic_registry_path is None else str(self._plant.semantic_registry_path), "semantic_sha256": None if semantic_registry is None else semantic_registry.semantic_sha256, "compile_count": self._plant.semantic_registry_compile_count},
        }

    def _problem_info(self, result: SolutionResult, audits: tuple[ActionChannelAudit, ...] = ()) -> dict[str, Any]:
        info = self._base_info(result)
        assert self._binding is not None and self._compiled_spaces is not None
        info.update({
            "problem": {"problem_id": self._binding.resolved_problem.problem_id, "problem_version": self._binding.resolved_problem.problem_version, "resolved_problem_sha256": self._binding.resolved_problem.resolved_problem_sha256},
            "runtime": {"runtime_binding_sha256": self._binding.runtime_binding_sha256, "observation_space_sha256": self._compiled_spaces.observation_space_sha256, "action_space_sha256": self._compiled_spaces.action_space_sha256, "preflight_status": self._preflight_status, "preflight_path": None if self._preflight_path is None else str(self._preflight_path)},
            "action_audit": [item.to_dict() for item in audits],
        })
        return info

    def _legacy_context(self, obs: dict[str, Any], result: SolutionResult, action: dict[str, Any] | None = None, *, step_index: int | None = None, time: Mapping[str, Any]) -> RuntimeStepContext:
        return TemporalRuntimeStepContext.create(time=time, step_index=self._step_index if step_index is None else step_index, observation=obs, requested_action=action or {}, applied_action=action or {}, realized_action={}, action_audit=(), internal_state={}, disturbances={}, parameters={}, constraints={}, availability={}, authority={"mode": "NATIVE"}, solution=result.to_dict(), previous_observation=None if self._current_context is None else dict(self._current_context.observation))

    def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
        if self._closed: raise RuntimeError("OpenDSSSimulator is closed.")
        self._episode_active = False
        self.history.clear(); self._step_index = 0
        self._last_result = None; self._current_context = None
        self._exogenous_binding = None; self._exogenous_last_audit = None
        self._forecast_private_audit = ()
        self._replay_session = None
        if self._replay_spec is not None:
            # Entire source/table/time preflight precedes any physical reset.
            self._replay_session = ReplaySession(self._replay_spec, options=options)
            spec = self._replay_session.episode_spec
            self._exogenous_spec, _ = self._replay_session.sample(0)
        else:
            spec = self._episode_spec.with_reset_options(options)
        self._episode_number += 1
        clock = EpisodeClock(spec, f"episode-{self._episode_number:06d}", seed)
        reset_time = clock.metadata(phase="reset", completed_steps=0)
        self._episode_clock = clock
        if self._forecast_noise.mode == "additive_gaussian":
            # Fail closed on undeclared sigma targets BEFORE any electrical
            # reset/solve; preflight one source sample without writing to Plant.
            source_oracle = ExogenousForecastOracle(
                clock=clock, replay_session=self._replay_session,
                replay_spec=self._replay_spec,
                explicit_source=None if self._replay_session is not None else self._exogenous_spec)
            first = source_oracle.request(0, 1)
            ForecastNoiseEngine(self._forecast_noise).validate_declared(first)
        super().reset(seed=seed)
        try:
            if self._problem_spec is None:
                if self._exogenous_spec is None:
                    result = self._plant.reset()
                    exogenous_info = None
                else:
                    self._plant.prepare_reset()
                    self._prepare_exogenous()
                    exogenous_info = self._apply_exogenous(0, reset_time)
                    result = self._plant.solve_snapshot()
                if exogenous_info is not None and not result.converged:
                    raise ExogenousApplicationError("A05I2_SNAPSHOT_NOT_CONVERGED")
                self._capture_exogenous_realized()
                obs = {"converged": int(result.converged)}
                info = self._base_info(result)
                info["time"] = reset_time
                if exogenous_info is not None: info["exogenous"] = exogenous_info
                context = self._legacy_context(obs, result, step_index=0, time=reset_time)
                self.history.append(context, phase="reset", reward=None, terminated=None, truncated=None, info=info)
            else:
                if self._initial_problem_context_prepared:
                    self._initial_problem_context_prepared = False
                else:
                    self._plant.prepare_reset()
                self._verify_binding_identity(); self._apply_static_configuration(); self._verify_static_configuration()
                self._prepare_exogenous()
                exogenous_info = self._apply_exogenous(0, reset_time)
                result = self._plant.solve_snapshot(); self._verify_static_configuration()
                if exogenous_info is not None and not result.converged:
                    raise ExogenousApplicationError("A05I2_SNAPSHOT_NOT_CONVERGED")
                self._capture_exogenous_realized()
                obs, raw_obs = self._read_observation()
                assert self._binding is not None
                disturbances = self._read_binding_values(self._binding.disturbance_bindings)
                parameters = self._read_binding_values(self._binding.parameter_bindings)
                constraints = self._read_binding_values(self._binding.constraint_bindings)
                internal = {sid: raw for sid, raw in raw_obs.items() if any(b.semantic_id == sid and b.source_registry.value == "state" for b in self._binding.observation_bindings)}
                context = TemporalRuntimeStepContext.create(time=reset_time, step_index=0, observation=obs, requested_action={}, applied_action={}, realized_action={}, action_audit=(), internal_state=internal, disturbances=disturbances, parameters=parameters, constraints=constraints, availability=self._availability(), authority=self._authority(), solution=result.to_dict())
                info = self._problem_info(result)
                info["time"] = reset_time
                if exogenous_info is not None: info["exogenous"] = exogenous_info
                full = self._read_full_state() if self.history.level in {HistoryLevel.H2, HistoryLevel.H3} or self.history.execution_profile is ExecutionProfile.AUDIT else None
                self.history.append(context, phase="reset", reward=None, terminated=None, truncated=None, info=info, full_state=full)
            self._last_result = result; self._current_context = context
            self._episode_active = True
            return obs, info
        except Exception:
            # Physical writes may already have occurred. Reset is mandatory.
            self._episode_active = False
            raise

    def step(self, action: dict[str, Any]) -> tuple[dict[str, Any], float, bool, bool, dict[str, Any]]:
        if self._closed: raise RuntimeError("OpenDSSSimulator is closed.")
        if not self._episode_active: raise RuntimeError("OpenDSSSimulator.step() requires an active reset episode; terminal or failed episodes must reset again.")
        if self._episode_clock is None: raise RuntimeError("A05 episode clock is unavailable before reset.")
        if self._episode_clock.is_horizon_exhausted(self._step_index):
            self._episode_active = False
            raise RuntimeError("Episode step limit has been exhausted; reset required.")
        if not self.action_space.contains(action):
            raise ValueError("Action does not satisfy the compiled OpenDSSSim Gym action space.")
        if not _finite(action):
            raise RuntimeActionError("NONFINITE_ACTION")
        next_step = self._step_index + 1
        step_time = self._episode_clock.metadata(phase="step", completed_steps=next_step)
        horizon = self._episode_clock.is_horizon_exhausted(next_step)
        strict_end = (self._replay_session is not None and
                      self._replay_session.last_strict_index(next_step - 1))
        step_time["horizon_exhausted"] = horizon
        if strict_end:
            step_time["data_exhausted"] = True
            step_time["truncation_reason"] = "data_exhausted"
        try:
            if self._problem_spec is None:
                exogenous_info = self._apply_exogenous(next_step - 1, step_time)
                result = self._plant.solve_snapshot()
                if exogenous_info is not None and not result.converged:
                    raise ExogenousApplicationError("A05I2_SNAPSHOT_NOT_CONVERGED")
                self._capture_exogenous_realized()
                obs = {"converged": int(result.converged)}
                info = self._base_info(result)
                context = self._legacy_context(obs, result, action, step_index=next_step, time=step_time)
                reward, terminated, truncated = 0.0, False, bool(horizon or strict_end)
                full = None
            else:
                assert self._binding is not None
                self._verify_static_configuration()
                exogenous_info = self._apply_exogenous(next_step - 1, step_time)
                applied, audits = self._decode_and_apply_actions(action)
                result = self._plant.solve_snapshot()
                self._verify_static_configuration()
                if exogenous_info is not None and not result.converged:
                    raise ExogenousApplicationError("A05I2_SNAPSHOT_NOT_CONVERGED")
                realized, audits = self._finalize_realized_actions(audits)
                self._capture_exogenous_realized()
                obs, raw_obs = self._read_observation()
                disturbances = self._read_binding_values(self._binding.disturbance_bindings)
                parameters = self._read_binding_values(self._binding.parameter_bindings)
                constraints = self._read_binding_values(self._binding.constraint_bindings)
                internal = {sid: raw for sid, raw in raw_obs.items() if any(b.semantic_id == sid and b.source_registry.value == "state" for b in self._binding.observation_bindings)}
                previous = None if self._current_context is None else dict(self._current_context.observation)
                context = TemporalRuntimeStepContext.create(time=step_time, step_index=next_step, observation=obs, requested_action=deepcopy(action), applied_action=applied, realized_action=realized, action_audit=audits, internal_state=internal, disturbances=disturbances, parameters=parameters, constraints=constraints, availability=self._availability(), authority=self._authority(), solution=result.to_dict(), previous_observation=previous)
                reward, terminated, custom_truncated = self._invoke_hooks(context)
                truncated = bool(custom_truncated or horizon or strict_end)
                info = self._problem_info(result, audits)
                full = self._read_full_state() if self.history.level in {HistoryLevel.H2, HistoryLevel.H3} or self.history.execution_profile is ExecutionProfile.AUDIT else None
            info["time"] = step_time
            if exogenous_info is not None: info["exogenous"] = exogenous_info
            self.history.append(context, phase="step", reward=reward, terminated=terminated, truncated=truncated, info=info, full_state=full)
            self._step_index = next_step
            self._last_result = result; self._current_context = context
            self._episode_active = not (terminated or truncated)
            return obs, reward, terminated, truncated, info
        except Exception:
            self._episode_active = False
            raise

    def native_diagnostics(self) -> dict[str, Any]:
        """Detached B00 research-only native diagnostics after authoritative solve.

        This is NOT part of controller_context(), A04 Gym spaces, or action
        authority. It never runs a solve and never returns a backend handle.
        A05 behavior when this is not called remains unchanged.
        """
        if self._closed or self._last_result is None or len(self.history) == 0:
            raise RuntimeError("B00_NATIVE_DIAGNOSTICS_REQUIRES_SOLVED_SNAPSHOT")
        method = getattr(self._plant.backend, "native_diagnostic_snapshot", None)
        if not callable(method):
            raise RuntimeError("B00_NATIVE_DIAGNOSTIC_BACKEND_UNAVAILABLE")
        result = method()
        if result.get("context_identity") != self.context_identity:
            raise RuntimeError("B00_NATIVE_DIAGNOSTIC_CONTEXT_IDENTITY_MISMATCH")
        if result.get("solution", {}).get("control_iterations") != self._last_result.control_iterations:
            raise RuntimeError("B00_NATIVE_DIAGNOSTIC_SOLVE_IDENTITY_MISMATCH")
        return deepcopy(result)

    def close(self) -> None:
        if self._closed: return
        self._plant.close(); self._closed = True; self._episode_active = False
