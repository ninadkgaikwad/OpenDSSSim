"""Shared, intentionally small helpers for *public API* educational clients.

Core rule: a controller can inspect its detached ControllerContext and encode
an action for env.step(); it must never mutate the AltDSS backend directly.

These utilities live OUTSIDE src/opendsssim/ to keep the simulator frozen.
"""
from __future__ import annotations
import csv
import hashlib
import json
import math
from pathlib import Path
from collections.abc import Mapping
from typing import Any
import numpy as np

COURSE = Path(__file__).resolve().parents[1]
REPO = COURSE.parents[1]
INPUT = COURSE / 'input'
OUTPUT = COURSE / 'output'
FEEDERS = ('ieee123_base','ieee123_pesgm2027',
           'ieee123_p2_mf01_simple','ieee123_p2_mf02_exotic')


def plain(value: Any) -> Any:
    """Make detached, finite, JSON-safe copies; never serialize engine objects."""
    if isinstance(value, np.ndarray): return plain(value.tolist())
    if isinstance(value, np.generic): return plain(value.item())
    if isinstance(value, Mapping): return {str(k):plain(v) for k,v in value.items()}
    if isinstance(value, (tuple,list)): return [plain(v) for v in value]
    if isinstance(value, (int,str,bool)) or value is None: return value
    if isinstance(value, float): return value if math.isfinite(value) else None
    return str(value)


def save_json(path:Path, value:Any) -> None:
    """Write output to an explicitly selected example run folder."""
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(plain(value),indent=2,sort_keys=True)+'\n',encoding='utf-8')


def save_csv(path:Path,rows:list[dict],fields:list[str]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader()
        w.writerows(rows)


def load_case(name:str)->dict:
    if name not in FEEDERS[1:]: raise ValueError('No MPC case for '+name)
    return json.loads((INPUT/'mpc_baseline'/'cases'/f'{name}_lindist_case.json').read_text())


def master(name:str)->Path:
    if name not in FEEDERS:raise ValueError('Unknown bundled IEEE-123 variant')
    p=INPUT/'feeders'/name/'IEEE123Master.dss'
    if not p.is_file():raise FileNotFoundError(p)
    return p


def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def verify_inputs()->dict:
    """Check every input against the committed course input SHA256 inventory."""
    index=INPUT/'SHA256_INPUT_MANIFEST.csv'
    with index.open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
    if not rows:raise RuntimeError('EMPTY_INPUT_MANIFEST')
    names=set()
    for item in rows:
        rel=Path(item['relative_path'])
        if rel.is_absolute() or '..' in rel.parts or str(rel).replace('\\','/')!=item['relative_path']:
            raise RuntimeError('UNSAFE_INPUT_PATH')
        p=COURSE/rel
        if p.resolve().is_relative_to(INPUT.resolve()) is False or p.is_symlink():
            raise RuntimeError('UNSAFE_INPUT_SYMLINK')
        if not p.is_file() or p.stat().st_size!=int(item['bytes']) or sha(p)!=item['sha256']:
            raise RuntimeError('INPUT_SHA256_MISMATCH: '+str(rel))
        names.add(rel.as_posix())
    actual={p.relative_to(COURSE).as_posix() for p in INPUT.rglob('*') if p.is_file() and p!=index}
    if actual!=names:raise RuntimeError(f'INPUT_FILE_SET_MISMATCH: {sorted(actual^names)}')
    return {'status':'PASS','verified_input_files':len(rows),'input_manifest_sha256':sha(index)}


def new_output(run_id:str)->Path:
    """Fail closed: never overwrite previous examples or write to feeder inputs."""
    if not run_id or len(run_id)>70 or not all(c.isascii() and (c.isalnum() or c in '_-') for c in run_id):
        raise ValueError('Run ID must use ASCII letters, digits, underscore or dash')
    result=OUTPUT/run_id
    if result.exists():raise FileExistsError('REFUSE_OVERWRITE_EXISTING_RUN: '+str(result))
    result.mkdir(parents=True,exist_ok=False)
    return result


def voltage_rows(obs:Mapping, *, step:int)->tuple[list[dict],dict]:
    """Read bus_voltage_pu strictly from the public observation mapping.

    The index is the OBSERVED COMPONENT INDEX, not an inferred physical A/B/C
    phase. Values ~0 indicate de-energization and are excluded from band checks.
    """
    rows=[];energized=[]
    for classname,objects in obs.get('current',{}).items():
        if classname.casefold()!='bus':continue
        for bus,features in objects.items():
            if 'bus_voltage_pu' not in features:continue
            a=np.asarray(features['bus_voltage_pu'],dtype=float).reshape(-1)
            for idx,v in enumerate(a,1):
                if not np.isfinite(v):raise ValueError('NONFINITE_BUS_VOLTAGE')
                live=float(v)>1e-4
                if live:energized.append(float(v))
                rows.append({'step':step,'bus':bus,'component_index':idx,'voltage_pu':float(v),
                             'energized':int(live),'outside_095_105':int(live and not .95<=v<=1.05)})
    if not energized:raise RuntimeError('NO_ENERGIZED_BUS_VOLTAGES_IN_OBSERVATION')
    return rows,{'step':step,'energized_components':len(energized),
                 'vmin_pu':min(energized),'vmax_pu':max(energized),
                 'outside_095_105':sum(not .95<=v<=1.05 for v in energized)}


def public_env(name:str,out:Path,*,problem=None,steps:int=3,replay:bool=False):
    """Construct simulator through its documented constructor, never Plant().

    Inventory, semantic registries, replay profiles and preflight receipts
    are stored beneath *this run's* output folder for reproducibility.
    """
    from opendsssim.environment import OpenDSSSimulator,EpisodeSpec
    kw=dict(network=master(name),problem=problem,
        inventory_dir=out/'inventory',semantic_registry_dir=out/'semantics',
        preflight_dir=out/'preflight')
    if replay:
        from experiments.pesgm2027.b00_native_controls.run_b00 import make_replay
        # Generate exogenous data explicitly. No opaque, simulator-private truth.
        profile,metadata=make_replay(feeder_dir=master(name).parent,
            output_dir=out/'generated_replay',steps=steps+14,
            start='2026-01-01T00:00:00Z',dt_seconds=3600,
            load_curve=(1.0,)*(steps+14),pv_curve=(1.0,)*(steps+14))
        kw['exogenous_replay']=profile
        save_json(out/'replay_provenance.json',metadata)
    else:
        kw['episode_spec']=EpisodeSpec(max_steps=steps,dt_seconds=3600)
    return OpenDSSSimulator(**kw)


def p1_problem():
    """Use original reference ProblemSpec factory; no bespoke action schema."""
    from opendsssim.controllers.reference import make_p1_problem
    data=load_case('ieee123_pesgm2027')
    return make_p1_problem(pv=tuple(x['entity'] for x in data['pv']),
        capacitors=tuple(x['entity'] for x in data['capacitors']),
        transformers=tuple(x['entity'] for x in data['taps']))


def p2_problem(name:str):
    from opendsssim.controllers.reference import make_p2_problem
    data=load_case(name)
    return make_p2_problem(switches=tuple(data['initial_switches']),
        curtailable_loads=tuple(x['entity'] for x in data['loads'] if x['curtailable']),
        faulted=tuple(x['name'] for x in data['branches'] if not x['healthy']))


def summary_action(audit):
    """Expose applied-vs-realized differences rather than overclaim success."""
    return [dict(semantic_id=a.get('semantic_id'),native_entity=a.get('native_entity'),
        status=a.get('status'),requested_value=plain(a.get('requested_value')),
        applied_value=plain(a.get('applied_value')),
        realized_value=plain(a.get('realized_value'))) for a in audit]


def closure(env):
    """Robust explicit release of an AltDSS context."""
    env.close()
