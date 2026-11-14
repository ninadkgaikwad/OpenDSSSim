"""Lesson 06: P1 RBC Volt/VAR via ControllerContext + complete Gym action.

The reference controller combines PV Volt/VAR droop, capacitor hysteresis and
regulator tap deadbands. The explicit PV `available_kw` here comes from the
static qualified input under constant replay; do not use it as an estimator
for real changing solar irradiance. Inspect action readback separately.
"""
from course_utils.core import public_env,p1_problem,load_case,save_csv,save_json,voltage_rows,summary_action
from course_utils.controllers import p1_rbc_spec

def run(out,steps):
    from opendsssim.controllers.reference import P1RuleBasedController
    from opendsssim.controllers.mpc.closed_loop_a07a2 import p1_case_from_json
    base=p1_case_from_json(load_case('ieee123_pesgm2027'))
    env=public_env('ieee123_pesgm2027',out,problem=p1_problem(),steps=steps,replay=True)
    history=[];voltages=[]
    try:
        obs,info=env.reset(seed=511)
        ctx=env.controller_context(include_static_network=True)
        controller=P1RuleBasedController(p1_rbc_spec(ctx,base))
        avail={pv.entity:pv.available_kw[0] for pv in base.pv}
        # This educational constant replay preserves current PV availability;
        # a dynamic replay must update this mapping from current public inputs.
        r,s=voltage_rows(obs,step=0);voltages+=r
        for i in range(steps):
            ctx=env.controller_context(include_static_network=True)
            action,decision=controller.decide(ctx,pv_available_kw=avail)
            if not env.action_space.contains(action):raise RuntimeError('P1_RBC_ACTION_NOT_IN_SPACE')
            obs,reward,terminated,truncated,info=env.step(action)
            if not info['solution']['converged']:raise RuntimeError('P1_RBC_AC_NONCONVERGENT')
            controller.on_success(ctx,action,info)
            r,s=voltage_rows(obs,step=i+1);voltages+=r
            history.append({'step':i+1,'voltage':s,'diagnostics':decision,
                            'action':action,'action_audit':summary_action(info.get('action_audit',[]))})
        save_json(out/'result.json',{'kind':'P1_RBC_EDUCATIONAL',
            'source_setup':'CASE_EXPLICIT_MONITOR_WIRING; NOT HISTORICAL_S10C_REPRODUCTION',
            'steps':history})
        save_csv(out/'observed_voltage.csv',voltages,list(voltages[0]))
        return {'completed_steps':len(history),'last_voltage':history[-1]['voltage']}
    finally:env.close()
