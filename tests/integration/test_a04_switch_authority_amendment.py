"""Genuine AltDSS successor checks with source and cache trees separated."""
from __future__ import annotations

from pathlib import Path
import shutil
import pytest

from opendsssim.environment.simulator import OpenDSSSimulator
from opendsssim.network.loading import CircuitSource
from opendsssim.problem import (
    ActionSpec,ControlAuthoritySpec,ControlAuthorityMode,ObservationSpec,
    ProblemSpec,RegistryKind,SelectionGroup,SemanticQuery,
)
from opendsssim.runtime import HistoryLevel,SemanticRuntimeAccess
from opendsssim.semantics.schema import NativePropertyAddress,RuntimeReadoutAddress

FIXTURE=Path(__file__).parents[1]/"fixtures"/"a03_semantic"/"Master.dss"


def _isolated_circuit(tmp_path):
    source=tmp_path/"circuit_source"
    source.mkdir()
    master=source/"Master.dss"
    shutil.copyfile(FIXTURE,master)
    return master,source


def _problem(hybrid):
    return ProblemSpec.create(
        "a04-switch-authority",f"h{int(hybrid)}",
        observations=ObservationSpec(groups=(SelectionGroup("obs",(
            SemanticQuery(RegistryKind.STATE,quantity="solution_converged"),)),)),
        actions=ActionSpec(groups=(SelectionGroup("switch",(
            SemanticQuery(RegistryKind.ACTION,native_entity="Line.Feeder",quantity="branch_switch_command"),)),)),
        control_authority=ControlAuthoritySpec(
            ControlAuthorityMode.HYBRID if hybrid else ControlAuthorityMode.EXTERNAL,
            external_entities=("Line.Feeder",),
            native_entities=("Capacitor.Cap1",) if hybrid else (),
        ),
    )


def _action(env,command):
    binding=next(b for b in env.runtime_binding.action_bindings
                 if b.entry.quantity=="branch_switch_command")
    root={};node=root
    for part in binding.path[:-1]:node=node.setdefault(part,{})
    node[binding.path[-1]]=command
    assert env.action_space.contains(root)
    return root


@pytest.mark.parametrize('hybrid',[False,True])
def test_live_switching_exclusive_authority_reset_and_preflight(tmp_path,hybrid):
    master,source=_isolated_circuit(tmp_path)
    # A02H1 hashes the ENTIRE source tree; never write inventory, preflight,
    # history or semantic cache underneath source or repeated reset must fail.
    state=tmp_path/"generated_state"
    options=dict(source_root=source,inventory_dir=state/"inv",
        semantic_registry_dir=state/"sem",preflight_dir=state/"pre",
        history_level=HistoryLevel.H3)
    source_hash=CircuitSource.from_path(master,source_root=source).source_tree_sha256
    statuses=[];binding_hashes=[]
    for trial in range(2):
        env=OpenDSSSimulator(master,problem=_problem(hybrid),**options)
        try:
            statuses.append(env.preflight_status)
            binding_hashes.append(env.runtime_binding.runtime_binding_sha256)
            assert tuple(name.casefold() for name in env.runtime_binding.disabled_native_controls)==('swtcontrol.sc1',)
            context_id=env.context_identity
            obs,_=env.reset()
            assert env.observation_space.contains(obs)
            access=SemanticRuntimeAccess(env._plant.backend)
            assert access.read(NativePropertyAddress('SwtControl.SC1','Enabled')) is False
            assert access.read(NativePropertyAddress('RegControl.RC1','Enabled')) is True
            assert access.read(NativePropertyAddress('CapControl.CC1','Enabled')) is True
            for step,command in enumerate((0,1),start=1):
                obs,reward,term,trunc,info=env.step(_action(env,command))
                assert env.context_identity==context_id
                assert env.observation_space.contains(obs)
                audit=info['action_audit'][0]
                assert audit['status']=='ADMISSIBLE_APPLIED'
                assert audit['requested_value']==command
                assert bool(audit['realized_value'][0]) is (command==0)
                assert bool(access.read(RuntimeReadoutAddress('CircuitElement','Line.Feeder','open_state'))[0]) is (command==0)
                assert access.read(NativePropertyAddress('SwtControl.SC1','Enabled')) is False
                assert len(env.history)==step+1 and env.history[step]['full_state']
            obs,_=env.reset()
            assert env.context_identity==context_id
            assert env.observation_space.contains(obs)
            assert len(env.history)==1
            assert access.read(NativePropertyAddress('SwtControl.SC1','Enabled')) is False
            assert CircuitSource.from_path(master,source_root=source).source_tree_sha256==source_hash
        finally:
            env.close()
    assert statuses==['BUILT','REUSED']
    assert binding_hashes[0]==binding_hashes[1]
