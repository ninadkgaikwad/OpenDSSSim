"""Lesson 04: declared exogenous replay and forecast-aware ControllerContext.

The physical replay source is explicit and written to this run's output.
The forecast is a public, authorized view; do not access hidden future truth.
"""
from course_utils.core import public_env,save_json,voltage_rows,save_csv

def run(out,steps):
    from experiments.pesgm2027.b00_native_controls.run_b00 import make_problem
    env=public_env('ieee123_pesgm2027',out,
          problem=make_problem('ieee123_pesgm2027'),steps=steps,replay=True)
    records=[];voltage=[]
    try:
        obs,info=env.reset(seed=511)
        rows,summary=voltage_rows(obs,step=0);voltage.extend(rows)
        for index in range(steps):
            ctx=env.controller_context(forecast_horizon=2,required=False)
            # A two-step oracle is allowed only for declared replay channels.
            record={'step':index+1,'forecast':None if ctx.forecast is None else ctx.forecast.to_dict(),
                    'decision_time':ctx.decision_time_utc,
                    'electrical_sample_time':ctx.electrical_sample_time_utc}
            obs,_,_,_,info=env.step({})
            rows,summary=voltage_rows(obs,step=index+1);voltage.extend(rows)
            record['post_control_voltage']=summary
            record['replay_info']=info.get('exogenous',{}).get('replay',{})
            records.append(record)
        result={'mode':'DECLARED_SYNTHETIC_CONSTANT_REPLAY','steps':steps,'records':records}
        save_json(out/'result.json',result)
        save_csv(out/'observed_voltage.csv',voltage,list(voltage[0]))
        print('Lesson 04: declared replay/forecast and observation voltages saved')
        return result
    finally:env.close()
