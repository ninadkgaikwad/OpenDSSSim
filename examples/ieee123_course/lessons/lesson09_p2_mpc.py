"""Lesson 09: P2 MPC, two lexicographic objective priorities, and AC feedback.

The original installed MILP is SLACK-FIRST. Optional SERVICE-FIRST is an
explicit experimental sensitivity and reorders ONLY two objective priorities
in an isolated in-memory solver copy, never a repository patch. Both enforce
the same hard fault, radiality and connectivity constraints.
"""
from course_utils.core import public_env,p2_problem,load_case,save_json,save_csv,voltage_rows,summary_action
from course_utils.controllers import public_action_audit,service_first_solve_function

def run(out,steps,name='ieee123_p2_mf01_simple',policy='slack-first'):
    from opendsssim.controllers.mpc.closed_loop_a07a2 import p2_case_from_json,step_once
    from opendsssim.controllers.mpc import p2_milp
    if policy not in ('slack-first','service-first'):raise ValueError('Unknown P2 objective policy')
    case=p2_case_from_json(load_case(name));faults=tuple(e.name for e in case.branches if not e.healthy)
    env=public_env(name,out,problem=p2_problem(name),steps=steps,replay=True)
    original=p2_milp.solve_p2
    policy_provenance={'policy':'ORIGINAL_FROZEN_SLACK_FIRST'}
    if policy=='service-first':
        alternative,policy_provenance=service_first_solve_function()
    history=[];voltages=[]
    try:
        obs,info=env.reset(seed=511)
        r,s=voltage_rows(obs,step=0);voltages+=r
        # The module pointer is replaced ONLY within this Python process and
        # restored in finally; no file is edited or private plant accessed.
        if policy=='service-first':p2_milp.solve_p2=alternative
        for i in range(steps):
            decision,action,executed=step_once(env,case,
                solve_kwargs={'time_limit_s':45,'threads':1,'output_flag':False},
                allow_apply=True)
            if executed is None:raise RuntimeError('P2_MPC_STEP_NOT_APPLIED')
            obs,info=executed
            matches=public_action_audit(info.get('action_audit',()),faults=faults)
            r,s=voltage_rows(obs,step=i+1);voltages+=r
            decision.update({'action':action,'actual_voltage':s,
                'healthy_switch_readbacks_matched':matches,
                'action_audit':summary_action(info.get('action_audit',()))})
            history.append(decision)
        save_json(out/'result.json',{'kind':'P2_MPC','scenario':name,
            'policy':policy,'policy_provenance':policy_provenance,
            'model_dt_hours':case.dt_hours,'physical_replay_dt_hours':1.,
            'nominal_energy_warning':'Model objective kWh does not represent delivered 24h AC energy',
            'thermal_security_claim':False,'steps':history})
        save_csv(out/'observed_voltage.csv',voltages,list(voltages[0]))
        return {'completed_steps':len(history),'status':[x['solver_status'] for x in history]}
    finally:
        p2_milp.solve_p2=original
        env.close()
