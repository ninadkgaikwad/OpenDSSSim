"""Lesson 01: load a circuit, reset, obtain native AC solution and discovery.

This intentionally uses ONLY public methods. Avoid `env._plant`, backend
handles, `altdss` mutation, or bare DSS commands in client/controller code.
"""
from course_utils.core import public_env,save_json,voltage_rows,save_csv,plain

def run(out,steps):
    env=public_env('ieee123_base',out,steps=1)
    try:
        engine=env.discover_engine()
        circuit=env.discover_circuit()
        obs,info=env.reset(seed=511)
        if not info['solution']['converged']:raise RuntimeError('AC reset failed')
        row,summary=voltage_rows(obs,step=0) if 'current' in obs else ([],{})
        inv=env.circuit_inventory
        result={'engine_type':type(engine).__name__,
                'circuit_type':type(circuit).__name__,
                'inventory_status':env.inventory_status,
                'inventory_objects':len(inv.objects) if inv else None,
                'inventory_buses':len(inv.buses) if inv else None,
                'solution':info['solution'],
                'observation_space':str(env.observation_space),
                'action_space':str(env.action_space),
                'reset_observation':obs,'voltage_summary':summary}
        save_json(out/'result.json',result)
        if row:save_csv(out/'observed_voltage.csv',row,list(row[0]))
        print('Lesson 01: native reset/AC solution and discovery saved')
        return result
    finally:env.close()
