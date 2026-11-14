"""B00I2 combined P0/P1/P2 no-action native time-series campaign."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json, math
from pathlib import Path
from experiments.pesgm2027.b00_native_controls.run_b00 import run_feeder,PRIMARY
from experiments.pesgm2027.b00_native_controls.b00i2_metrics import analyze,write_metrics,profiles
from experiments.pesgm2027.b00_native_controls.render_b00i2 import render_to_file

def campaign(repo_root:Path,output_root:Path,*,steps:int=24,dt_seconds:int=3600,seed:int=511):
    if output_root.exists():raise ValueError('B00I2_REFUSE_EXISTING_OUTPUT_ROOT')
    if output_root.resolve().is_relative_to(repo_root.resolve()):raise ValueError('B00I2_OUTPUT_MUST_BE_OUTSIDE_REPOSITORY')
    output_root.mkdir(parents=True,exist_ok=False)
    load,pv=profiles(steps);summary=[]
    for feeder in PRIMARY:
        result=run_feeder(repo_root=repo_root,output_root=output_root,feeder=feeder,steps=steps,seed=seed,
                          dt_seconds=dt_seconds,load_curve=load,pv_curve=pv,history_level='H2',native_diagnostics=True)
        metrics=analyze(result,dt_seconds)
        out=output_root/feeder
        write_metrics(metrics,out)
        render_to_file(out/'b00i2_metrics.json',out/'result.json',out/'b00i2_dashboard.html')
        summary.append({'feeder':feeder,'scenario':'P2_PRE' if 'p2' in feeder else 'NATIVE_AS_INSTALLED',
            'result_sha256':sha256((out/'result.json').read_bytes()).hexdigest().upper(),
            'metrics_sha256':sha256((out/'b00i2_metrics.json').read_bytes()).hexdigest().upper(),
            'render_sha256':sha256((out/'b00i2_dashboard.html').read_bytes()).hexdigest().upper(),
            'p0':metrics['p0_status'],'p1':metrics['p1_status'],'p2':metrics['p2_status'],
            'loss_energy_kwh':metrics['integrated_loss_kwh'],
            'net_tap_change_proxy':metrics['net_tap_change_proxy']})
        print(f'B00I2_FEEDER={feeder} P0=PASS P1=PASS P2=PASS_BOUNDARY',flush=True)
    campaign_doc={'schema':'B00I2.combined_campaign.v01','seed':seed,'steps':steps,'dt_seconds':dt_seconds,
                  'profiles':'SYNTHETIC_DIAGNOSTIC_NOT_FIELD_DATA','results':summary,
                  'scope':'Four ratified IEEE123 native-controls cases. NO restoration or external actions.',
                  'limitations':'Static control queue/event readbacks do not validate physical delay modeling.',
                  'R01':'OPEN','R02':'OPEN_MITIGATION_QUALIFIED'}
    (output_root/'b00i2_campaign.json').write_text(json.dumps(campaign_doc,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    links=''.join(f'<li><a href="{x["feeder"]}/b00i2_dashboard.html">{x["feeder"]}</a> — loss energy {x["loss_energy_kwh"]:.2f} kWh</li>' for x in summary)
    (output_root/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>B00I2 four IEEE-123 feeders</title><style>body{font:17px system-ui;margin:6%;max-width:850px}li{margin:18px}</style><h1>B00I2 — four IEEE-123 baselines</h1><p>Recorder-derived offline dashboards. Synthetic profiles, static native controls, no external actions.</p><ul>'+links+'</ul><p>R01/R02 open. B00 science freeze requires separate sign-off.</p>',encoding='utf-8')
    return campaign_doc

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo-root',type=Path,required=True);p.add_argument('--output-root',type=Path,required=True)
    p.add_argument('--steps',type=int,default=24);p.add_argument('--dt-seconds',type=int,default=3600);p.add_argument('--seed',type=int,default=511)
    args=p.parse_args();campaign(args.repo_root.resolve(),args.output_root.resolve(),steps=args.steps,dt_seconds=args.dt_seconds,seed=args.seed)
if __name__=='__main__':main()
