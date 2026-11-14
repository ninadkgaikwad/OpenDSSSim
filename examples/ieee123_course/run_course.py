#!/usr/bin/env python3
"""IEEE-123 course command-line entry point.

Examples:
    python examples/ieee123_course/run_course.py --list
    python examples/ieee123_course/run_course.py --lesson 00 --run-id check_001
    python examples/ieee123_course/run_course.py --all --steps 3 --run-id tutorial_001
    python examples/ieee123_course/run_course.py --paper-campaign --steps 24 --run-id pesgm_001

Outputs NEVER overwrite prior runs. A failure saves partial progress and
stops. Source, DSS feeder, controllers and plant are never patched.
"""
from __future__ import annotations
import argparse
import datetime as dt
import importlib
import sys
import traceback
from pathlib import Path

# Support launch from anywhere by making this course root importable.
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'src'))

LESSONS={
 '00':('lessons.lesson00_input_integrity','Input pins / provenance'),
 '01':('lessons.lesson01_snapshot_discovery','AC reset and circuit discovery'),
 '02':('lessons.lesson02_problem_and_spaces','ProblemSpec / Gym action-observation spaces'),
 '03':('lessons.lesson03_clock_history','Time, history and native step'),
 '04':('lessons.lesson04_replay_forecast','Physical replay and forecasts'),
 '05':('lessons.lesson05_controller_context','Detached controller context'),
 '06':('lessons.lesson06_p1_rbc','P1 rule-based Volt/VAR controller'),
 '07':('lessons.lesson07_p1_mpc','P1 Gurobi MIQP receding-horizon controller'),
 '08':('lessons.lesson08_p2_rbc','P2 RBC route continuation + AC'),
 '09':('lessons.lesson09_p2_mpc','P2 Gurobi MILP receding-horizon controller'),
 '10':('lessons.lesson10_visualize','Plot archived reference results'),
}

def targets(args):
    if args.paper_campaign:
        # This is a matched-duration reference CAMPAIGN, not a claim of matched
        # controller policy; P2 RBC is replay of previously screened routes.
        return [('P1_RBC','06',{}),('P1_MPC','07',{}),
          ('P2_MF01_RBC','08',{'name':'ieee123_p2_mf01_simple'}),
          ('P2_MF01_MPC','09',{'name':'ieee123_p2_mf01_simple','policy':'service-first'}),
          ('P2_MF02_RBC','08',{'name':'ieee123_p2_mf02_exotic'}),
          ('P2_MF02_MPC','09',{'name':'ieee123_p2_mf02_exotic','policy':'service-first'})]
    if args.all:
        return [(f'lesson_{key}',key,
            {'name':args.variant} if key in ('08','09') else {}) for key in LESSONS]
    extra=({'name':args.variant} if args.lesson in ('08','09') else {})
    if args.lesson=='09':extra['policy']=args.policy
    return [(f'lesson_{args.lesson}',args.lesson,extra)]

def main():
    a=argparse.ArgumentParser(description='Self-contained IEEE-123 OpenDSSSim educational campaign')
    group=a.add_mutually_exclusive_group(required=True)
    group.add_argument('--lesson',choices=tuple(LESSONS))
    group.add_argument('--all',action='store_true')
    group.add_argument('--paper-campaign',action='store_true')
    group.add_argument('--list',action='store_true')
    a.add_argument('--run-id',default=None,help='Unique ASCII label for output/<run-id>')
    a.add_argument('--steps',type=int,default=3,help='1..24 steps (paper campaign typically 24)')
    a.add_argument('--variant',choices=('ieee123_p2_mf01_simple','ieee123_p2_mf02_exotic'),
                   default='ieee123_p2_mf01_simple')
    a.add_argument('--policy',choices=('slack-first','service-first'),default='slack-first')
    args=a.parse_args()
    if args.list:
        for key,(module,label) in LESSONS.items():print(f'  {key}  {label}')
        print('  --paper-campaign  six RBC/MPC P1/P2 native 24-step runs')
        return 0
    if not 1<=args.steps<=24:a.error('--steps must be 1..24')
    from course_utils.core import verify_inputs,new_output,save_json
    if args.run_id is None:
        args.run_id='run_'+dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    # Do not create an output run for an invalid / tampered input release.
    print('CHECK_INPUTS:',verify_inputs())
    out=new_output(args.run_id)
    record={'schema':'OpenDSSSim.IEEE123Course.v1','run_id':args.run_id,
        'started_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
        'source_modified':False,'public_env_only':True,'steps_requested':args.steps,
        'lessons':[], 'status':'RUNNING'}
    save_json(out/'campaign_receipt.json',record)
    try:
        for label,key,kw in targets(args):
            print(f'\n=== {label}: {LESSONS[key][1]} ===',flush=True)
            resultdir=out/label
            resultdir.mkdir(exist_ok=False)
            lesson=importlib.import_module(LESSONS[key][0])
            result=lesson.run(resultdir,args.steps,**kw)
            record['lessons'].append({'name':label,'lesson':key,'status':'PASS',
                                      'output':resultdir.relative_to(HERE).as_posix(),
                                      'summary':result})
            save_json(out/'campaign_receipt.json',record)
        record['status']='PASS_COMPLETE';return 0
    except BaseException as exc:
        record['status']='FAIL_REVIEW_REQUIRED'
        record['error']=type(exc).__name__+': '+str(exc)
        record['traceback']=traceback.format_exc()
        print(record['traceback'],file=sys.stderr)
        return 3
    finally:
        record['finished_utc']=dt.datetime.now(dt.timezone.utc).isoformat()
        save_json(out/'campaign_receipt.json',record)
        print('RECEIPT='+str(out/'campaign_receipt.json'),flush=True)

if __name__=='__main__':raise SystemExit(main())
