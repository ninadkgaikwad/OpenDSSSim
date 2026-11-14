"""Lesson 08: P2 RBC graph preview and S10D-selected-route native continuation.

Critical limitation: the installed P2GraphController.preview() is structural
only. A real *new* P2GraphController.decide() requires a qualified electrical
evaluator callback. This lesson checks the current graph preview against an
ORIGINAL ELECTRICALLY SCREENED S10D route and reuses the route. It never
invents a fresh electrical-evaluator result, and every official env.step is
verified using new native AC voltage/readbacks.
"""
from course_utils.core import public_env,p2_problem,load_case,save_json,save_csv,voltage_rows,summary_action
from course_utils.controllers import archived_s10d_states,p2_loads,public_action_audit

def run(out,steps,name='ieee123_p2_mf01_simple'):
    from opendsssim.controllers.reference import P2GraphController,encode_action
    from opendsssim.controllers.mpc.closed_loop_a07a2 import p2_case_from_json
    case=p2_case_from_json(load_case(name))
    faults=tuple(e.name for e in case.branches if not e.healthy)
    route,states,archived=archived_s10d_states(name)
    controller=P2GraphController(loads=p2_loads(case),faulted=faults)
    env=public_env(name,out,problem=p2_problem(name),steps=steps,replay=True)
    history=[];voltages=[]
    try:
        obs,info=env.reset(seed=511)
        r,s=voltage_rows(obs,step=0);voltages+=r
        for i in range(steps):
            ctx=env.controller_context(forecast_horizon=2,required=False,include_static_network=True)
            preview=controller.preview(ctx)
            expected={key.lower():bool(value) for key,value in preview.states.items()}
            if expected!=states:raise RuntimeError('CURRENT_STRUCTURAL_PREVIEW_DIFFERS_FROM_QUALIFIED_S10D_ROUTE')
            if preview.action is not None:raise RuntimeError('STRUCTURAL_PREVIEW_MUST_NOT_ISSUE_ACTION')
            commands={}
            for entry in ctx.action_layout:
                cls,obj,quantity=entry['path'];key=(cls+'.'+obj).lower()
                if quantity!='branch_switch_command' or key not in states:
                    raise RuntimeError('UNEXPECTED_P2_ACTION_CHANNEL')
                commands[(cls+'.'+obj,quantity)]='CLOSED' if states[key] else 'OPEN'
            action=encode_action(ctx,commands)
            if not env.action_space.contains(action):raise RuntimeError('P2_RBC_ILLEGAL_ACTION')
            demand=0.0;connected=0
            from opendsssim.controllers.reference.contracts import observed
            for load in controller.loads:
                if preview.service[load.native_entity]>0.5:
                    connected+=1
                    demand+=float(observed(ctx,load.native_entity,'load_available_active_demand_kw'))
            obs,reward,terminated,truncated,info=env.step(action)
            if not info['solution']['converged']:raise RuntimeError('RBC_P2_NONCONVERGENT_AC_STEP')
            matches=public_action_audit(info.get('action_audit',()),faults=faults)
            r,s=voltage_rows(obs,step=i+1);voltages+=r
            history.append({'step':i+1,'route':route,'nominal_connected_kw_proxy':demand,
                'connected_load_count':connected,'voltage':s,
                'healthy_switch_readbacks_matched':matches,
                'structural_preview_diagnostics':preview.diagnostics,
                'action_audit':summary_action(info.get('action_audit',()))})
        save_json(out/'result.json',{'kind':'P2_RBC_S10D_SELECTED_ROUTE_CONTINUATION',
             'scenario':name,'route':route,'fresh_RBC_electrical_evaluator_per_step':False,
             'AC_validation_per_step':True,'steps':history})
        save_csv(out/'observed_voltage.csv',voltages,list(voltages[0]))
        return {'completed_steps':len(history),'nominal_connected_kw':history[-1]['nominal_connected_kw_proxy']}
    finally:env.close()
