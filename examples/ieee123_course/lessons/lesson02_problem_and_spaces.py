"""Lesson 02: create a ProblemSpec, understand resolved Gym dict spaces.

The ProblemSpec selects semantic observations/actions. The *compiled* layout
contains exact entity paths, numeric shapes, domains and stable hashes. An
unauthorized action cannot be smuggled through the framework by a controller.
"""
from course_utils.core import public_env,p1_problem,save_json,plain

def run(out,steps):
    problem=p1_problem()
    env=public_env('ieee123_pesgm2027',out,problem=problem,steps=1)
    try:
        obs,info=env.reset(seed=511)
        ctx=env.controller_context(include_static_network=True)
        result={'problem_id':problem.problem_id,
                'problem_spec_sha256':problem.problem_spec_sha256,
                'resolved_problem_sha256':env.resolved_problem.resolved_problem_sha256,
                'observation_space_sha256':ctx.observation_space_sha256,
                'action_space_sha256':ctx.action_space_sha256,
                'action_layout':ctx.to_dict()['action_layout'],
                'device_commandability':ctx.to_dict()['devices'],
                'observation_keys':list(obs),
                'official_spaces':{'observation':str(env.observation_space),
                                   'action':str(env.action_space)},
                'current_obs_in_space':bool(env.observation_space.contains(obs)),
                'preflight_status':env.preflight_status}
        if not result['current_obs_in_space']:raise RuntimeError('Gym observation invalid')
        save_json(out/'result.json',result)
        print('Lesson 02: ProblemSpec / Gym contract identity saved')
        return result
    finally:env.close()
