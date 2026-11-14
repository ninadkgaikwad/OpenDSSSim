"""A07A2 guarded, contract-first native MPC experimental pilot.

Offline native snapshots provide fixed approximate model matrices only.
Online information and all actions pass through official OpenDSSSim public API.
Run with --mode inspect for zero control actions; --mode pilot solves Gurobi and
applies receding-horizon first actions through env.step(). Results exploratory.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
import traceback
import numpy as np

VARIANTS=('ieee123_pesgm2027','ieee123_p2_mf01_simple','ieee123_p2_mf02_exotic')

class PilotError(RuntimeError):pass

def _sha(p):return sha256(Path(p).read_bytes()).hexdigest().upper()

def _json(v):
    if isinstance(v,dict):return {str(k):_json(x) for k,x in v.items()}
    if isinstance(v,(tuple,list)):return [_json(x) for x in v]
    if isinstance(v,np.ndarray):return _json(v.tolist())
    if isinstance(v,np.generic):return _json(v.item())
    if isinstance(v,(bool,int,str)) or v is None:return v
    if isinstance(v,float):return v if np.isfinite(v) else None
    return repr(v)

def _voltage_summary(observation):
    vals=[]
    for cls,names in observation.get('current',{}).items():
        if cls.casefold()!='bus':continue
        for obj,entry in names.items():
            if 'bus_voltage_pu' in entry:
                a=np.asarray(entry['bus_voltage_pu'],dtype=float).reshape(-1)
                vals.extend(float(x) for x in a if np.isfinite(x) and x>1e-4)
    return {'energized_phase_count':len(vals),'min_pu':min(vals) if vals else None,
        'max_pu':max(vals) if vals else None,
        'outside_095_105_count':sum(x<.95 or x>1.05 for x in vals)}

def _check_static_sources(repo,base,feeder):
    model=base/'cases'/(feeder+'_lindist_case.json')
    snapshot=base/'cases'/(feeder+'_native_parameters.json')
    if not model.is_file() or not snapshot.is_file():raise PilotError('PINNED_CASE_FILES_MISSING')
    pins=json.loads((base/'CASE_PINS.json').read_text(encoding='utf8'))
    for name,expected in pins['files_sha256'].items():
        p=base/name
        if not p.is_file() or _sha(p)!=expected:raise PilotError('STATIC_CASE_HASH_DRIFT:'+name)
    master=repo/'experiments'/'pesgm2027'/'feeders'/feeder/'IEEE123Master.dss'
    if _sha(master)!=json.loads(snapshot.read_text())['source_master_sha256'].upper():
        raise PilotError('LIVE_FEEDER_MASTER_DRIFT')
    return json.loads(model.read_text(encoding='utf8'))

def _replay(repo,feeder,out,max_samples):
    # Reuse the already-existing B00 declared physical profile contract, not
    # private simulator access; signals are explicit and synthetically constant.
    from experiments.pesgm2027.b00_native_controls.run_b00 import make_replay
    curves=(1.,)*max_samples
    return make_replay(feeder_dir=repo/'experiments'/'pesgm2027'/'feeders'/feeder,
        output_dir=out,steps=max_samples,
        start='2026-01-01T00:00:00Z',dt_seconds=3600,
        load_curve=curves,pv_curve=curves)[0]

def run(repo,base,out,feeder,mode,steps,time_limit,seed,declared_replay):
    from opendsssim.environment import OpenDSSSimulator
    from opendsssim.controllers.reference import make_p1_problem,make_p2_problem
    from opendsssim.controllers.mpc.closed_loop_a07a2 import (
        p1_case_from_json,p2_case_from_json,update_p1,update_p2,step_once)
    from opendsssim.environment.clock import EpisodeSpec
    d=_check_static_sources(repo,base,feeder)
    case=p1_case_from_json(d) if feeder==VARIANTS[0] else p2_case_from_json(d)
    if feeder==VARIANTS[0]:
        pv=tuple(x.entity for x in case.pv)
        caps=tuple(x.entity for x in case.capacitors)
        taps=tuple(x.entity for x in case.taps)
        problem=make_p1_problem(pv=pv,capacitors=caps,transformers=taps)
        static=json.loads((base/'cases'/'ieee123_pesgm2027_static_discovery.json').read_text())
        reference={}
        for row in static['native_discovery']['objects']:
            if row['full_name'].casefold().startswith('pvsystem.'):
                reference[row['full_name'].casefold()]=float(json.loads(row['properties_json'])['Irradiance'])
        if set(reference)!={x.entity.casefold() for x in case.pv}:
            raise PilotError('OFFLINE_PV_REFERENCE_INCOMPLETE')
    else:
        switches=tuple(case.initial_switches)
        faulted=tuple(x.name for x in case.branches if not x.healthy)
        curt=tuple(x.entity for x in case.loads if x.curtailable)
        problem=make_p2_problem(switches=switches,curtailable_loads=curt,faulted=faulted)
        reference=None
    env_spec={
        'network':repo/'experiments'/'pesgm2027'/'feeders'/feeder/'IEEE123Master.dss',
        'problem':problem,
        'inventory_dir':out/'inventory','semantic_registry_dir':out/'semantics',
        'preflight_dir':out/'preflight',
    }
    if declared_replay:
        env_spec['exogenous_replay']=_replay(repo,feeder,out,max_samples=steps+case.horizon+1)
    else:
        env_spec['episode_spec']=EpisodeSpec(max_steps=steps)
    records=[]
    env=OpenDSSSimulator(**env_spec)
    try:
        obs,info=env.reset(seed=seed)
        if not info['solution']['converged']:raise PilotError('RESET_AC_NOT_CONVERGED')
        initial={'initial_voltage':_voltage_summary(obs),
            'problem_spec_sha256':problem.problem_spec_sha256,
            'case_kind':type(case).__name__,'prediction_horizon':case.horizon,
            'replay_mode':'DECLARED_B00_SYNTHETIC_CONSTANT' if declared_replay else 'NO_EXOGENOUS_PERSISTENCE',
            'reset_snapshot_converged':True}
        # Inspect the actual authorized layout and initial model conversion.
        ctx=env.controller_context(forecast_horizon=case.horizon,required=False,include_static_network=True)
        if type(case).__name__=='P1Case':
            converted,why=update_p1(case,ctx,pv_reference_irradiance=reference)
        else:converted,why=update_p2(case,ctx)
        initial.update({'action_channels':len(ctx.action_layout),
            'forecast_conversion':why,'model_contract':converted.validate() is converted,
            'action_space_sha256':ctx.action_space_sha256,
            'observation_space_sha256':ctx.observation_space_sha256,
            'network_inventory_semantic_sha256':ctx.static_network.inventory_semantic_sha256})
        if mode=='inspect':
            return {'status':'PASS_A07A2_REAL_OPENDSSIM_INSPECTION_NO_GUROBI_NO_ACTION',
                'initial':initial,'steps':[],'closed_loop_executed':False,
                'official_env_step_executed':False}
        if mode!='pilot':raise PilotError('INVALID_MODE')
        for i in range(steps):
            receipt, action, outcome=step_once(env,case,pv_reference_irradiance=reference,
                solve_kwargs={'time_limit_s':time_limit,'threads':1,'output_flag':False},
                allow_apply=True)
            if outcome is None:raise PilotError('CONTROL_STEP_NOT_EXECUTED')
            now,stepinfo=outcome
            receipt['actual_voltage_envelope']=_voltage_summary(now)
            receipt['native_action_audit_statuses']=[a['status'] for a in stepinfo.get('action_audit',[])]
            records.append(receipt)
            if (stepinfo['time'].get('completed_steps')!=i+1):
                raise PilotError('OFFICIAL_EPISODE_CLOCK_DID_NOT_ADVANCE')
            if receipt['terminated'] or receipt['truncated']:
                if i<steps-1:raise PilotError('EARLY_TERMINATION')
                break
        if len(records)!=steps:raise PilotError('NATIVE_CONTROL_STEP_COUNT_MISMATCH')
        return {'status':'PASS_A07A2_EXPLORATORY_NATIVE_CLOSED_LOOP_PENDING_INDEPENDENT_AUDIT',
            'initial':initial,'steps':records,'closed_loop_executed':True,
            'official_env_step_executed':True,
            'thermal_security_claim':False,
            'AC_sensitivity_validated':False,
            'frozen_solver_predicted_voltage_trajectory_exported':False}
    finally:
        env.close()

def main():
    a=argparse.ArgumentParser()
    a.add_argument('--repo-root',type=Path,required=True)
    a.add_argument('--baseline-root',type=Path,required=True)
    a.add_argument('--output-root',type=Path,required=True)
    a.add_argument('--feeder',choices=VARIANTS,required=True)
    a.add_argument('--mode',choices=('inspect','pilot'),required=True)
    a.add_argument('--steps',type=int,default=24)
    a.add_argument('--time-limit-s',type=float,default=45.)
    a.add_argument('--seed',type=int,default=511)
    a.add_argument('--no-replay',action='store_true')
    x=a.parse_args()
    if not 1<=x.steps<=24 or not 1<=x.time_limit_s<=600:raise SystemExit('Invalid bounded pilot arguments')
    if x.output_root.exists():raise SystemExit('REFUSE_OVERWRITE_EXISTING_OUTPUT_ROOT')
    if not x.repo_root.is_dir() or not x.baseline_root.is_dir():raise SystemExit('MISSING_REPO_OR_BASELINE')
    if x.output_root.resolve().is_relative_to(x.repo_root.resolve()):raise SystemExit('NO_RESULTS_INSIDE_REPOSITORY')
    x.output_root.mkdir(parents=True,exist_ok=False)
    results={'schema':'MPC_A07A2.exploratory_native_closed_loop.v1',
       'variant':x.feeder,'mode':x.mode,'utc':datetime.now(timezone.utc).isoformat(),
       'source_modified':False,'Gurobi_solver_executed':x.mode=='pilot'}
    code=0
    try:
        result=run(x.repo_root,x.baseline_root,x.output_root,x.feeder,x.mode,
                   x.steps,x.time_limit_s,x.seed,not x.no_replay)
        results.update(result)
    except BaseException as exc:
        results.update({'status':'FAIL_A07A2_REVIEW_REQUIRED',
            'error':f'{type(exc).__name__}:{exc}','traceback':traceback.format_exc(),
            'no_success_claim':True});code=3
    (x.output_root/'A07A2_RESULTS.json').write_text(json.dumps(_json(results),indent=2,sort_keys=True)+'\n',encoding='utf8')
    print(json.dumps({'status':results['status'],'output':str(x.output_root/'A07A2_RESULTS.json')},indent=2))
    return code

if __name__=='__main__':sys.exit(main())
