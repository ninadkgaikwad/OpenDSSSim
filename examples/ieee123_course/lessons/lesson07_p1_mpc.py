"""Lesson 07: P1 MPC mathematical optimization and first-action receding horizon.

The captured horizon-12 MIQP is updated using only public ControllerContext
and authorized forecasts, then Gurobi solves and the FIRST action passes
through env.step(). The mathematical model is an approximation: the native
AC solution is the authoritative realized electrical response.
"""
import json
from pathlib import Path
from course_utils.core import public_env,p1_problem,load_case,INPUT,save_json,save_csv,voltage_rows,summary_action

def run(out,steps):
    from opendsssim.controllers.mpc.closed_loop_a07a2 import p1_case_from_json,step_once
    case=p1_case_from_json(load_case('ieee123_pesgm2027'))
    static=json.loads((INPUT/'mpc_baseline/cases/ieee123_pesgm2027_static_discovery.json').read_text())
    pv_reference={}
    for item in static['native_discovery']['objects']:
        if item['full_name'].lower().startswith('pvsystem.'):
            pv_reference[item['full_name'].lower()]=float(json.loads(item['properties_json'])['Irradiance'])
    assert len(pv_reference)==10,'Captured reference PV discovery incomplete'
    env=public_env('ieee123_pesgm2027',out,problem=p1_problem(),steps=steps,replay=True)
    records=[];voltages=[]
    try:
        obs,info=env.reset(seed=511)
        r,s=voltage_rows(obs,step=0);voltages+=r
        for i in range(steps):
            # `step_once` uses ControllerContext, solves the installed P1 MIQP
            # and encodes a legal complete action. It calls official env.step.
            decision,action,executed=step_once(env,case,
                pv_reference_irradiance=pv_reference,
                solve_kwargs={'time_limit_s':45,'threads':1,'output_flag':False},
                allow_apply=True)
            if executed is None:raise RuntimeError('P1_MPC_ACTION_NOT_EXECUTED')
            obs,info=executed
            r,s=voltage_rows(obs,step=i+1);voltages+=r
            decision.update({'actual_voltage':s,'action':action,
                'action_audit':summary_action(info.get('action_audit',[]))})
            records.append(decision)
        save_json(out/'result.json',{'kind':'P1_MPC','steps':records,
            'model_horizon':case.horizon,'physical_replay_dt_hours':1.0,
            'all_AC_plants_converged':True})
        save_csv(out/'observed_voltage.csv',voltages,list(voltages[0]))
        return {'completed_steps':len(records),'solver_statuses':[x['solver_status'] for x in records]}
    finally:env.close()
