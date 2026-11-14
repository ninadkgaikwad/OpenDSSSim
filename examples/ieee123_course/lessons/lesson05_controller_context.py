"""Lesson 05: controller information entitlement and detached context.

`ControllerContext` is a safe value object. It includes the exact action
layout, authorized device readiness, optional forecast, static graph, and
last realized feedback, but NO mutable AltDSS or Plant handle.
"""
from course_utils.core import public_env,p2_problem,save_json

def run(out,steps):
    env=public_env('ieee123_p2_mf01_simple',out,
        problem=p2_problem('ieee123_p2_mf01_simple'),steps=1)
    try:
        obs,info=env.reset(seed=511)
        ctx=env.controller_context(forecast_horizon=2,required=False,
                                    include_static_network=True)
        result=ctx.to_dict()
        # The controller is handed values, not an engine or a private handle.
        if any(k.startswith('_') for k in result):raise RuntimeError('Private context field')
        save_json(out/'result.json',result)
        print('Lesson 05: read-only controller context, devices and topology exported')
        return {'authorized_action_channels':len(ctx.action_layout),
                'static_network_elements':len(ctx.static_network.elements)}
    finally:env.close()
