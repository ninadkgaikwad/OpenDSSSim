"""Lesson 10: make results/geometry figures with ZERO simulator requirement.

Uses supplied IEEE-123 diagram coordinates, not geographic positions. Plotting
an archived reference file does not claim a new simulation was executed.
"""
from pathlib import Path
import csv
from course_utils.core import INPUT,save_json

def run(out,steps):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    path=INPUT/'reference_results/qualified_voltage_envelopes.csv'
    with path.open(newline='',encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
    if not rows:raise RuntimeError('EMPTY_REFERENCE_DATA')
    # Show the actual recorded column names first; input file schemas may
    # differ between qualifying experiments. Do not guess a phase mapping.
    schema=list(rows[0])
    xkey=next((k for k in schema if k.lower() in ('step','sample','step_index')),None)
    minkey=next((k for k in schema if k.lower() in ('vmin_pu','min_pu','minimum_voltage_pu')),None)
    maxkey=next((k for k in schema if k.lower() in ('vmax_pu','max_pu','maximum_voltage_pu')),None)
    runkey=next((k for k in schema if k.lower() in ('experiment','scenario','controller','series','run')),None)
    report={'schema':schema,'rows':len(rows),'source':'QUALIFIED_ARCHIVED_V06_NOT_NEW_SIMULATION'}
    if xkey and minkey and maxkey:
        groups={}
        for r in rows:
            try:x=float(r[xkey]);lo=float(r[minkey]);hi=float(r[maxkey])
            except (TypeError,ValueError):continue
            label=r.get(runkey,'Reference') if runkey else 'Reference'
            groups.setdefault(label,[]).append((x,lo,hi))
        fig,ax=plt.subplots(figsize=(9,5))
        for key,entries in list(groups.items())[:8]:
            entries.sort()
            ax.plot([a[0] for a in entries],[a[1] for a in entries],label=f'{key} minimum')
            ax.plot([a[0] for a in entries],[a[2] for a in entries],ls='--',label=f'{key} maximum')
        ax.axhline(.95,ls=':',color='gray');ax.axhline(1.05,ls=':',color='gray')
        ax.set(xlabel=xkey,ylabel='Voltage (pu)',title='Archived IEEE-123 voltage envelopes')
        ax.legend(fontsize=6,ncol=2);fig.tight_layout()
        fig.savefig(out/'voltage_envelopes.png',dpi=180)
        fig.savefig(out/'voltage_envelopes.svg');plt.close(fig)
        report['plot']='voltage_envelopes.svg'
    save_json(out/'result.json',report)
    print('Lesson 10: archived reference schema and optional plot exported')
    return report
