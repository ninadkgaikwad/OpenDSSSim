"""A05I2 native physics tests on both actual frozen IEEE123 feeder folders."""
from pathlib import Path
import math
import pytest

from opendsssim.environment import (
    OpenDSSSimulator, EpisodeSpec, ExogenousProfileSpec, LoadSeries, PVSeries,
    ExogenousBindingError, ExogenousApplicationError,
)
from opendsssim.semantics.schema import NativePropertyAddress
from opendsssim.runtime.access import SemanticRuntimeAccess

FEEDERS = Path(__file__).resolve().parents[2] / "experiments" / "pesgm2027" / "feeders"


def _read(env, native, prop):
    return float(SemanticRuntimeAccess(env._plant.backend).read(NativePropertyAddress(native, prop)))


@pytest.mark.parametrize("feeder", ["ieee123_base", "ieee123_pesgm2027"])
def test_ieee123_l1_option_a_readback_and_unbound_baseline(tmp_path, feeder):
    source = ExogenousProfileSpec("explicit-loaded", loads=(LoadSeries(
        ("Load.S1a",), "absolute_pq", ((32, 11), (25, -5)),
    ),))
    env = OpenDSSSimulator(FEEDERS / feeder / "IEEE123Master.dss",
                           exogenous=source, episode_spec=EpisodeSpec(max_steps=2),
                           inventory_dir=tmp_path/"inventory", semantic_registry_dir=tmp_path/"semantic")
    try:
        original = env._plant.backend.solve_snapshot
        solves = [0]
        def counted():
            solves[0] += 1
            return original()
        env._plant.backend.solve_snapshot = counted
        _, first = env.reset()
        assert solves[0] == 1 and first["solution"]["converged"]
        assert first["exogenous"]["sample_index"] == 0
        assert env._exogenous_last_audit["bindings"][0]["terminal_powers_kw_kvar"]
        assert len(env._exogenous_last_audit["bindings"][0]["native_kw_kvar"]) == 2
        assert _read(env, "Load.S1a", "kW") == pytest.approx(32)
        assert _read(env, "Load.S1a", "kvar") == pytest.approx(11)
        assert _read(env, "Load.S2b", "kW") == pytest.approx(20)
        _, _, _, _, one = env.step({})
        assert solves[0] == 2 and one["solution"]["converged"]
        assert one["time"]["electrical_sample_time_utc"] == first["time"]["electrical_sample_time_utc"]
        assert one["exogenous"]["sample_index"] == 0
        assert _read(env, "Load.S1a", "kW") == pytest.approx(32)
        _, _, _, truncated, two = env.step({})
        assert solves[0] == 3 and truncated and two["solution"]["converged"]
        assert two["exogenous"]["sample_index"] == 1
        assert _read(env, "Load.S1a", "kW") == pytest.approx(25)
        assert _read(env, "Load.S1a", "kvar") == pytest.approx(-5)
        assert len(env.history) == 3
        _, reread = env.reset()
        assert solves[0] == 4 and reread["exogenous"]["sample_index"] == 0
        assert _read(env, "Load.S1a", "kW") == pytest.approx(32)
    finally:
        env.close()


def test_ieee123_l2_fanout_baseline_preservation_and_l3_leading_pf(tmp_path):
    source = ExogenousProfileSpec("typed-three-modes", loads=(
        LoadSeries(("Load.S1a", "Load.S2b"), "multiplier", (0.8, 0.6)),
        LoadSeries(("Load.S4c",), "p_signed_pf", ((30.0, -0.8), (25.0, 1.0))),
    ))
    env = OpenDSSSimulator(FEEDERS / "ieee123_base" / "IEEE123Master.dss", exogenous=source,
                           episode_spec=EpisodeSpec(max_steps=2), inventory_dir=tmp_path/"inv",
                           semantic_registry_dir=tmp_path/"sem")
    try:
        _, info = env.reset()
        assert info["solution"]["converged"]
        assert _read(env, "Load.S1a", "kW") == pytest.approx(32)
        assert _read(env, "Load.S1a", "kvar") == pytest.approx(16)
        assert _read(env, "Load.S2b", "kW") == pytest.approx(16)
        assert _read(env, "Load.S2b", "kvar") == pytest.approx(8)
        assert _read(env, "Load.S4c", "kvar") == pytest.approx(-22.5)
        env.step({})
        env.step({})
        assert _read(env, "Load.S1a", "kW") == pytest.approx(24)
        assert _read(env, "Load.S4c", "kvar") == pytest.approx(0)
    finally:
        env.close()


def test_p1_working_feeder_pv_irradiance_faiman_and_nominal_temperature(tmp_path):
    source = ExogenousProfileSpec("p1-poa-weather", pvs=(
        PVSeries(("PVSystem.PVD47",), (0.8, 0.5), (20, 20), (5, 0)),
        PVSeries(("PVSystem.PVD76",), (0.7, 0.1)),
    ))
    env = OpenDSSSimulator(FEEDERS / "ieee123_pesgm2027" / "IEEE123Master.dss",
                           exogenous=source, episode_spec=EpisodeSpec(max_steps=2),
                           inventory_dir=tmp_path/"inv", semantic_registry_dir=tmp_path/"sem")
    try:
        _, info = env.reset()
        assert info["solution"]["converged"]
        assert info["exogenous"]["temperature_extension_version"] == "A05I2.pv-temperature-whitelist.v1"
        assert _read(env, "PVSystem.PVD47", "Irradiance") == pytest.approx(0.8)
        assert _read(env, "PVSystem.PVD47", "Temperature") == pytest.approx(20 + 800/(25+6.84*5))
        assert _read(env, "PVSystem.PVD76", "Temperature") == pytest.approx(25)
        assert _read(env, "PVSystem.PVD47", "Pmpp") == pytest.approx(210)
        assert _read(env, "PVSystem.PVD47", "kvar") == pytest.approx(0)
        env.step({})
        _, _, _, _, two = env.step({})
        assert two["solution"]["converged"]
        assert _read(env, "PVSystem.PVD47", "Temperature") == pytest.approx(40)
        assert _read(env, "PVSystem.PVD76", "Temperature") == pytest.approx(25)
        assert _read(env, "PVSystem.PVD47", "Pmpp") == pytest.approx(210)
    finally:
        env.close()


def test_fail_closed_invalid_native_target_and_strict_missing_sample(tmp_path):
    bad = ExogenousProfileSpec("unknown-device", loads=(LoadSeries(("Load.NOT_PRESENT",), "multiplier", (1.0,)),))
    env = OpenDSSSimulator(FEEDERS / "ieee123_base" / "IEEE123Master.dss", exogenous=bad,
                           inventory_dir=tmp_path/"inv", semantic_registry_dir=tmp_path/"sem")
    try:
        with pytest.raises(ExogenousBindingError, match="Unknown"):
            env.reset()
        assert len(env.history) == 0
        with pytest.raises(RuntimeError, match="reset"):
            env.step({})
    finally:
        env.close()
    good = ExogenousProfileSpec("one-sample", loads=(LoadSeries(("Load.S1a",), "multiplier", (1.0,)),))
    env = OpenDSSSimulator(FEEDERS / "ieee123_base" / "IEEE123Master.dss", exogenous=good,
                           episode_spec=EpisodeSpec(max_steps=3), inventory_dir=tmp_path/"inv2",
                           semantic_registry_dir=tmp_path/"sem2")
    try:
        env.reset()
        env.step({})
        assert len(env.history) == 2
        with pytest.raises(ExogenousApplicationError, match="REQUIRED_SAMPLE"):
            env.step({})
        assert len(env.history) == 2
        with pytest.raises(RuntimeError, match="reset"):
            env.step({})
    finally:
        env.close()


def test_p1_external_pv_q_remains_a04_action_and_exogenous_cannot_write_it(tmp_path):
    import numpy as np
    from opendsssim.problem import (ActionSpec, ControlAuthorityMode, ControlAuthoritySpec,
        ObservationSpec, ProblemSpec, RegistryKind, SelectionGroup, SemanticQuery)
    problem = ProblemSpec.create(
        "a05i2-p1-q-authority", "1",
        observations=ObservationSpec(groups=(SelectionGroup("obs", (
            SemanticQuery(RegistryKind.STATE, quantity="solution_converged"),)),)),
        actions=ActionSpec(groups=(SelectionGroup("pv", (
            SemanticQuery(RegistryKind.ACTION, native_entity="PVSystem.PVD47", quantity="pv_reactive_power_command"),)),)),
        control_authority=ControlAuthoritySpec(ControlAuthorityMode.EXTERNAL, external_entities=("PVSystem.PVD47",)),
    )
    source = ExogenousProfileSpec("q-separation", pvs=(PVSeries(("PVSystem.PVD47",), (0.9,)),))
    env = OpenDSSSimulator(FEEDERS / "ieee123_pesgm2027" / "IEEE123Master.dss",
                           problem=problem, exogenous=source, episode_spec=EpisodeSpec(max_steps=1),
                           inventory_dir=tmp_path/"inv", semantic_registry_dir=tmp_path/"sem",
                           preflight_dir=tmp_path/"pre")
    try:
        env.reset()
        b = next(x for x in env.runtime_binding.action_bindings if x.entry.quantity == "pv_reactive_power_command")
        action, curr = {}, None
        curr = action
        for part in b.path[:-1]:
            curr = curr.setdefault(part, {})
        curr[b.path[-1]] = np.array(12.0, dtype=np.float64)
        assert env.action_space.contains(action)
        _, _, _, truncated, info = env.step(action)
        assert truncated and info["solution"]["converged"]
        assert info["action_audit"][0]["status"] == "ADMISSIBLE_APPLIED"
        assert _read(env, "PVSystem.PVD47", "kvar") == pytest.approx(12)
        assert _read(env, "PVSystem.PVD47", "Irradiance") == pytest.approx(0.9)
    finally:
        env.close()
