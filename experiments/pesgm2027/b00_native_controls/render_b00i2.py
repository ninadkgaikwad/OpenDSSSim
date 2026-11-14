"""Offline standalone HTML renderer. Reads recorder JSON; never accesses a solver."""
from __future__ import annotations
import argparse
from html import escape
import json
import math
from pathlib import Path
from experiments.pesgm2027.b00_native_controls.b00i2_metrics import RecorderError

def _plot(rows, title, key, unit, color):
    vals=[r.get(key) for r in rows]
    points=[(i,float(v)) for i,v in enumerate(vals) if isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(float(v))]
    if not points:
        return '<section><h3>'+escape(title)+'</h3><p class="na">Not available in recorder</p></section>'
    low=min(v for _,v in points); high=max(v for _,v in points)
    if low==high:low-=1;high+=1
    coords=' '.join(f'{40 + 850*i/max(len(rows)-1,1):.1f},{160-120*(v-low)/(high-low):.1f}' for i,v in points)
    return ('<section><h3>'+escape(title)+'</h3><svg viewBox="0 0 920 190" role="img" aria-label="'+escape(title)+'">'
        '<line x1="40" y1="160" x2="895" y2="160" stroke="#9ca3af"/>'
        '<line x1="40" y1="20" x2="40" y2="160" stroke="#9ca3af"/>'
        f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2.7"/>'
        f'<text x="45" y="17" font-size="12">Max {high:.3f} {escape(unit)}</text>'
        f'<text x="45" y="178" font-size="12">Min {low:.3f} {escape(unit)}</text>'
        f'<text x="868" y="180" font-size="12">n={len(rows)}</text></svg></section>')

def render(metrics:dict, result:dict) -> str:
    if metrics.get('schema')!='B00I2.metrics.v01' or metrics.get('feeder') != result.get('feeder'):
        raise RecorderError('RENDER_RECORDER_IDENTITY_MISMATCH')
    rows=metrics['rows']; feeder=escape(str(result['feeder']))
    def val(x):return 'Unavailable' if x is None else escape(str(x))
    cards=''.join(f'<article class="stat"><b>{escape(name)}</b><span>{val(value)}</span></article>' for name,value in [
        ('Loss energy (kWh)',round(metrics['integrated_loss_kwh'],3)),
        ('Net tap changes (proxy)',metrics['net_tap_change_proxy']),
        ('Net capacitor changes (proxy)',metrics['net_capacitor_state_change_proxy']),
        ('RegControls enabled',f"{rows[-1]['regcontrols_enabled']}/{rows[-1]['regcontrols_total']}"),
        ('Native mode','STATIC (readback)'),('P2 queue data','Post-solve only')])
    plots=''.join([_plot(rows,'Minimum energized voltage','vmin_nonzero_pu','pu','#0d9488'),
        _plot(rows,'Maximum voltage','vmax_pu','pu','#2563eb'),
        _plot(rows,'Active feeder losses','loss_p_kw','kW','#c2410c'),
        _plot(rows,'Control iterations','control_iterations','count','#7c3aed'),
        _plot(rows,'Pending native queue (post solve)','queue_pending_post_solve','count','#a16207'),
        _plot(rows,'Net tap-change proxy','tap_net_changes_proxy','changes','#db2777')])
    cols=('sample_index','timestamp_utc','loss_p_kw','vmin_nonzero_pu','vmax_pu','control_iterations','tap_net_changes_proxy','queue_pending_post_solve','event_log_entries_new')
    table_rows=''.join('<tr>'+''.join(f'<td>{val(r.get(k))}</td>' for k in cols)+'</tr>' for r in rows)
    caveats=''.join('<li>'+escape(str(c))+'</li>' for c in metrics['science_caveats'])
    head='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>B00I2</title><style>
    body{font:15px system-ui,-apple-system,Segoe UI,sans-serif;color:#172334;background:#f4f7fa;margin:0;padding:24px;max-width:1250px;margin:auto}
    h1{font-size:26px}.muted{color:#607188}.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
    .stat,section{background:white;border:1px solid #dde5ea;border-radius:12px;padding:17px;margin-bottom:14px}
    .stat b{display:block;font-size:12px;color:#637083}.stat span{font-size:19px;font-weight:650}
    .charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,440px),1fr));gap:14px}svg{width:100%;height:auto}
    h3{font-size:15px;margin:0 0 9px}table{width:100%;border-collapse:collapse;font-size:12px}th,td{border-bottom:1px solid #e5e7eb;text-align:left;padding:8px}.scroll{overflow-x:auto}
    .na{color:#b45309}li{margin:5px 0}</style></head><body>'''
    heading='<h1>B00I2 · '+feeder+'</h1><p class="muted">Recorder-derived native control diagnostics · synthetic profiles · no extra electrical solves</p>'
    table='<section><h3>Recorded samples</h3><div class="scroll"><table><thead><tr>'+''.join('<th>'+escape(x)+'</th>' for x in ('#','timestamp UTC','loss kW','Vmin pu','Vmax pu','control iter','tap Δ proxy','queue pending','log Δ'))+'</tr></thead><tbody>'+table_rows+'</tbody></table></div></section>'
    return head+heading+'<div class="stats">'+cards+'</div><div class="charts">'+plots+'</div>'+table+'<section><h3>Scientific boundaries</h3><ul>'+caveats+'</ul></section></body></html>'

def render_to_file(metrics_file:Path,result_file:Path,html_file:Path):
    metrics=json.loads(metrics_file.read_text(encoding='utf-8'))
    result=json.loads(result_file.read_text(encoding='utf-8'))
    html_file.write_text(render(metrics,result),encoding='utf-8')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--metrics',type=Path,required=True);parser.add_argument('--result',type=Path,required=True);parser.add_argument('--html',type=Path,required=True)
    args=parser.parse_args();render_to_file(args.metrics,args.result,args.html)
if __name__=='__main__':main()
