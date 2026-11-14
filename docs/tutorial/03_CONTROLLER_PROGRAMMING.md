# Tutorial 3 — Programming P1/P2 RBC and MPC

## P1 RBC: all channels must be issued together

The P1 problem selects 10 `PVSystem` reactive commands, four physical capacitor-bank commands and seven transformer tap commands. `P1RuleBasedController.decide(ctx, pv_available_kw=...)` implements PV droop, capacitor hysteresis and regulator deadband. **The supplied present-time `pv_available_kw` is an explicit caller-owned input**; do not infer it from hidden future source values or assign an arbitrary headroom. Lesson 06's constant synthetic replay uses the qualified static case's initial PV availability and labels it as such.

The controller emits a **complete action**, and `P1RuleBasedController.on_success` is called only after a successful native step. This is important for stateful fallback/hysteresis. The reference controller's monitor wiring is explicit `P1Spec(monitors=..., kva=..., tap_step=..., tap_winding_index=...)`; different feeders require their own mapping. The educational wiring is not claimed to be byte-identical to the historic RBC S10C study.

## P1 MPC: horizon 12 and first-action principle

The frozen P1 MIQP uses calibrated offline LinDistFlow matrices plus authorized current observations. `p1_case_from_json`, `update_p1` and `step_once` integrate the model without bypassing the simulator. C83 has three physical phase injections but **one shared physical bank decision** (qualified A07A3 repair). The Gurobi solver returns a horizon-12 plan; only its **first** action is applied, and the next decision uses new `ControllerContext`/AC results.

Do not conflate the optimization's predicted voltage trajectory with native AC. A converged solver is not proof of a converged plant step. This is why lessons export native observed bus-voltage components.

## P2 RBC: difference between `preview()` and `decide()`

`P2GraphController.preview(ctx)` computes bus-level source-connected, radial candidate topologies without a physical command. It **must not** be treated as a native-validated switching policy. `P2GraphController.decide(ctx)` needs a separately qualified nonmutating electrical-evaluator callback and refuses to issue a physical action otherwise.

The learning campaign therefore reuses the **original S10D electrically screened MF01/MF02 routes** while recalculating structural preference at every step. The route is applied through `encode_action(ctx, ...)` and `env.step()`, with 24 independent native AC observations. This is a **selected-route continuation**, not 24 independent electrical route optimizations. MF01 includes a fault-disabled switch, and its audit status is expected to differ from a healthy-switch applied result.

## P2 MPC: two policies, one physical model

- **Slack-first (original):** lexicographically minimize operational voltage/thermal slack, then weighted unserved load, then switching effort.
- **Service-first (explicit sensitivity):** lexicographically minimize weighted unserved load, then operational slack, then switching effort; fault, connectivity and radiality remain hard.

Lesson 09 uses the installed `p2_milp.py` for slack-first; service-first copies the exact solver text **in memory**, checks its SHA-256, replaces only the two priority numbers and restores the module function pointer in a `finally` block. This is an advanced *comparison technique*, not guidance to patch the frozen simulator. Gurobi remains optional and separately licensed.

Both P2 problems have horizon 2 with `case.dt_hours=0.25`, whereas the course replay is hourly. The 24h connected-demand proxy is calculated from static/source connectivity, not from the model objective's two 15-minute intervals.

## New controller template

```python
class MyController:
    def decide(self, ctx):
        # 1. Inspect only ctx.observation, action_layout, device statuses,
        #    and explicitly declared forecast/static network.
        # 2. Compute a COMPLETE mapping for every selected action channel.
        # 3. Produce Gym-compatible values, never raw backend writes.
        commands = {}
        for entry in ctx.action_layout:
            cls, device, quantity = entry['path']
            # Determine a physically defensible value for this quantity.
            # Do not invent the value: use an actual rule/optimization policy.
            raise NotImplementedError('Supply an explicit controller policy')
        from opendsssim.controllers.reference import encode_action
        return encode_action(ctx, commands)
```

The example deliberately refuses to return a fake command until you supply an actual policy. Your controller should work against `ControllerContext` and the compiled action-space contract, not the physical backend. If a novel actuator is needed, propose a **general-purpose simulator capability change** separately—never bury it in a controller patch.

## Fair-comparison checklist

Fix and document source circuit, faults, profile, seed, horizon, actuator authority, observation/forecast entitlement, interval, voltage band, history level, solver settings and realized-action checks. Describe RBC selected-route replay separately from MPC's new per-step optimization. For P1 RBC/MPC preserve existing differences and never describe the archived 24-step runs as perfectly matched unless they truly are. See `docs/development/control_science/common/Fair_Comparison_Contract.md`.
