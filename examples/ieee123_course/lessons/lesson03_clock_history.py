"""Lesson 03: temporal snapshot replay, logical clock and history recorder.

Native baseline has NO external actuator authority. The exact {} action is
legal. This is the safest first full Gym reset->step loop to understand.
"""
from course_utils.core import public_env,save_json,plain

def run(out,steps):
    from experiments.pesgm2027.b00_native_controls.run_b00 import make_problem
    env=public_env('ieee123_base',out,problem=make_problem('ieee123_base'),steps=steps)
    records=[]
    try:
        obs,info=env.reset(seed=511)
        records.append({'kind':'reset','time':info['time'],'solution':info['solution']})
        for index in range(steps):
            ctx=env.controller_context(include_static_network=(index==0))
            action={}
            if not env.action_space.contains(action):raise RuntimeError('Native {} action forbidden')
            obs,reward,terminated,truncated,info=env.step(action)
            if not info['solution']['converged']:raise RuntimeError('AC non-convergence')
            if info['time']['completed_steps']!=index+1:raise RuntimeError('Clock did not advance')
            records.append({'kind':'step','time':info['time'],'solution':info['solution'],
                            'reward':reward,'terminated':terminated,'truncated':truncated,
                            'controller_decision_time':ctx.decision_time_utc,
                            'electrical_sample_time':ctx.electrical_sample_time_utc,
                            'native_action_audits':info.get('action_audit',[])})
        result={'steps':steps,'history_entries':len(env.history),'snapshots':records,
            'important':'Logical time is separate from the native Snapshot engine time.'}
        save_json(out/'result.json',result)
        print('Lesson 03: Gym clock/history records saved')
        return result
    finally:env.close()
