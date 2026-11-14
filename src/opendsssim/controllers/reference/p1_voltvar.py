"""P1 deterministic local simultaneous Volt/VAR, capacitor and tap RBC.

Authoritative science: P1_Reference_Controller.md; all monitor mappings and
operating information are explicit, not inferred from future or privileged data.
"""
from __future__ import annotations
from dataclasses import dataclass
from copy import deepcopy
from math import isfinite,sqrt
from typing import Mapping
import numpy as np
from .contracts import ControllerContractError, bound_for, observed, require_ready, encode_action

@dataclass(frozen=True)
class P1Monitor:
    bus: str
    indices: tuple[int,...] = ()  # zero-based positions in native Bus.puVmagAngle magnitude readout
    reduction: str = 'AVG'

@dataclass(frozen=True)
class P1Spec:
    monitors: Mapping[str,P1Monitor]
    kva: Mapping[str,float]
    tap_step: Mapping[str,float]
    tap_winding_index: Mapping[str,int]
    pv_full_pos: float=0.95
    pv_zero_pos: float=0.99
    pv_zero_neg: float=1.01
    pv_full_neg: float=1.05
    cap_on: float=0.97
    cap_off: float=1.03
    tap_reference: float=1.0
    tap_band: float=0.025

    def __post_init__(self):
        if not self.pv_full_pos<self.pv_zero_pos<=self.pv_zero_neg<self.pv_full_neg:
            raise ControllerContractError('Invalid PV curve ordering')
        if self.cap_on>=self.cap_off or self.tap_band<=0:
            raise ControllerContractError('Invalid hysteresis/deadband')

def pv_normalized_q(v:float, spec:P1Spec):
    if v<=spec.pv_full_pos:return 1.0
    if v<spec.pv_zero_pos:return (spec.pv_zero_pos-v)/(spec.pv_zero_pos-spec.pv_full_pos)
    if v<=spec.pv_zero_neg:return 0.0
    if v<spec.pv_full_neg:return -(v-spec.pv_zero_neg)/(spec.pv_full_neg-spec.pv_zero_neg)
    return -1.0

class P1RuleBasedController:
    def __init__(self,spec:P1Spec):
        self.spec=spec
        self.last_successful_command=None
        self.last_episode=None

    def _voltage(self,ctx,entity):
        key=next((k for k in self.spec.monitors if k.casefold()==entity.casefold()),None)
        if key is None:raise ControllerContractError('P1 monitor not configured: '+entity)
        m=self.spec.monitors[key]
        a=np.asarray(observed(ctx,'Bus.'+m.bus,'bus_voltage_pu'),dtype=float).reshape(-1)
        if not a.size or not np.all(np.isfinite(a)):
            raise ControllerContractError('Invalid monitored bus voltages')
        if m.indices:
            if any(i<0 or i>=a.size for i in m.indices):raise ControllerContractError('Monitor index not in bus shape')
            a=a[list(m.indices)]
        if m.reduction=='AVG':v=float(np.mean(a))
        elif m.reduction=='MIN':v=float(np.min(a))
        elif m.reduction=='MAX':v=float(np.max(a))
        else:raise ControllerContractError('Unsupported monitor reducer')
        return v

    def decide(self,ctx,*,pv_available_kw:Mapping[str,float]):
        """Compute all requests from ONE detached current ControllerContext.

        `pv_available_kw` is caller-supplied current-time availability, never
        forecast truth or inferred from requested reactive commands.
        """
        if self.last_episode!=ctx.episode_id:
            self.last_episode=ctx.episode_id;self.last_successful_command=None
        commands={}; diagnostics=[]
        for entry in ctx.action_layout:
            path=tuple(entry['path']);entity=path[0]+'.'+path[1];quantity=path[2]
            require_ready(ctx,entity)
            v=self._voltage(ctx,entity)
            if quantity=='pv_reactive_power_command':
                source=next((k for k in pv_available_kw if k.casefold()==entity.casefold()),None)
                rated=next((k for k in self.spec.kva if k.casefold()==entity.casefold()),None)
                if source is None or rated is None:raise ControllerContractError('PV present-time headroom data missing: '+entity)
                p=float(pv_available_kw[source]);s=float(self.spec.kva[rated])
                if not isfinite(p) or not isfinite(s) or s<=0 or p<0 or p>s+1e-7:
                    raise ControllerContractError('Invalid PV availability/rating: '+entity)
                vset=pv_normalized_q(v,self.spec)*sqrt(max(s*s-p*p,0.0))
                if entry['low'] is not None:vset=max(vset,float(entry['low']))
                if entry['high'] is not None:vset=min(vset,float(entry['high']))
                value=float(vset)
            elif quantity=='capacitor_state':
                prev=np.asarray(observed(ctx,entity,'capacitor_state'),dtype=float)
                if prev.shape!=tuple(entry['shape']) or np.any((prev!=0)&(prev!=1)):
                    raise ControllerContractError('Capacitor state array invalid: '+entity)
                if v<=self.spec.cap_on:value=np.ones(prev.shape,dtype=float)
                elif v>=self.spec.cap_off:value=np.zeros(prev.shape,dtype=float)
                else:value=prev.copy()
            elif quantity=='transformer_tap_command':
                prev=np.asarray(observed(ctx,entity,'transformer_tap_position'),dtype=float).reshape(-1)
                key=next((k for k in self.spec.tap_step if k.casefold()==entity.casefold()),None)
                wkey=next((k for k in self.spec.tap_winding_index if k.casefold()==entity.casefold()),None)
                if key is None or wkey is None:raise ControllerContractError('Missing tap step/winding contract')
                i=int(self.spec.tap_winding_index[wkey]); step=float(self.spec.tap_step[key])
                if i<0 or i>=len(prev) or not isfinite(step) or step<=0:
                    raise ControllerContractError('Invalid tap data')
                direction=1 if v<self.spec.tap_reference-self.spec.tap_band/2 else (-1 if v>self.spec.tap_reference+self.spec.tap_band/2 else 0)
                value=float(prev[i]+direction*step)
                if entry['low'] is not None:value=max(value,float(entry['low']))
                if entry['high'] is not None:value=min(value,float(entry['high']))
            else:raise ControllerContractError('Unknown P1 action quantity: '+quantity)
            commands[(entity,quantity)]=value
            diagnostics.append({'entity':entity,'quantity':quantity,'v_monitor_pu':v,'request':value.tolist() if isinstance(value,np.ndarray) else value})
        if not commands:raise ControllerContractError('Empty P1 action set')
        return encode_action(ctx,commands),tuple(diagnostics)

    def on_success(self,ctx,applied_action,info):
        """Update memory only after an A04-successful step/audit, not on request."""
        if not info['solution']['converged'] or any(a['status']!='ADMISSIBLE_APPLIED' for a in info['action_audit']):
            raise ControllerContractError('No successful P1 realized action to memorize')
        self.last_successful_command=deepcopy(applied_action)

    def fallback(self,ctx,reason:str):
        if ctx.episode_id!=self.last_episode or self.last_successful_command is None:
            raise ControllerContractError('NO_SUCCESSFUL_P1_ACTION_AVAILABLE_FOR_FALLBACK')
        return deepcopy(self.last_successful_command), {'fallback':True,'reason':str(reason),'source':'last_successful_action'}
