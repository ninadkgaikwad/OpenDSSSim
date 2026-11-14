# A03.4 — Class-by-Class Semantic Policy

## 1. Purpose

This file is the authoritative A03-v1 policy that prevents raw AltDSS writability from
being confused with OpenDSSSim control semantics.

The policy is generalized by native DSS class and physical meaning. It must not contain
IEEE-123 paper object names.

## 2. Policy table

| Native entity | State semantics | Action semantics | Disturbance semantics | Intrinsic constraint semantics | Parameter semantics | Default mutability |
|---|---|---|---|---|---|---|
| `Load` | realized electrical operating quantities/readouts | none by default | active/reactive demand | intrinsic model/domain metadata only when justified | kV, phases, connection, model/configuration | demand `STEP_EXOGENOUS`; config `INIT_ONLY` |
| `PVSystem` | realized P/Q and terminal electrical readouts | reactive-power command | active-power availability/driver | kVA/inverter capability and reactive limits when available | kVA, `Pmpp`, phases, connection/config | Q `STEP_CONTROLLABLE`; availability `STEP_EXOGENOUS`; rating `INIT_ONLY/READ_ONLY` |
| `Storage` | realized P/Q, energy/SOC and operating readouts when supported | active/reactive dispatch | externally supplied availability/event driver when applicable | kW/kVA/energy/SOC domains | kW/kWh/kVA ratings, connection/config | dispatch `STEP_CONTROLLABLE`; ratings `INIT_ONLY/READ_ONLY` |
| `Capacitor` | realized switching/state readout | capacitor state command | none normally | allowed discrete state domain | kvar, kV, phases/config | state `STEP_CONTROLLABLE`; config `INIT_ONLY` |
| `Transformer` / `AutoTrans` | realized taps, powers, currents | tap command/movement when semantically controllable | none normally | min/max/discrete tap and ratings | winding kV/kVA, impedance, NumTaps/config | tap `STEP_CONTROLLABLE`; physical config `INIT_ONLY` |
| `Line` | currents, powers, losses, energized/open readout | open/close only when semantically switchable | outage/event driver later | NormAmps/EmergAmps; switch domain when switchable | impedance, length, phases, terminals | switching `STEP_CONTROLLABLE`; event `STEP_EXOGENOUS`; config `INIT_ONLY` |
| `Generator` | realized P/Q and terminal electrical readouts | dispatch only when explicit generator-control semantics are enabled | availability/profile driver when modeled | rating/dispatch domains when available | ratings/configuration | dispatch `STEP_CONTROLLABLE`; availability `STEP_EXOGENOUS`; config `INIT_ONLY` |
| `Bus` | voltage/pu-voltage/node readouts | none | none | none by default | base/topological identity where available | `READ_ONLY` |
| circuit-element runtime service | currents, powers, losses, terminal quantities | only explicit supported operations | none | references device-specific limits | structural identity | readouts `READ_ONLY` |
| `Solution` | convergence/status readout | none | none | none | solver identity/config where separately modeled | `READ_ONLY` |
| `Topology` | connectivity/isolation/loop readout | topology changes occur through switchable device commands | future outage/event input | problem radiality/restoration rules are later `ProblemSpec` unless intrinsically physical | structural connectivity | state `READ_ONLY` |
| `RegControl` | native-controller status/configuration readout when useful | not the physical external tap action | none | native controller setting domains | VReg, Band, delays, winding/control binding | generally `INIT_ONLY` |
| `CapControl` | native-controller state/configuration | not the physical capacitor action | none | native setting domains | on/off settings, monitored/controlled bindings | generally `INIT_ONLY` |
| `InvControl` | native-control status/configuration | does not automatically create external DER actions | none | controller-setting domains | modes/curves/DER bindings | generally `INIT_ONLY` |
| `ExpControl` | native-control status/configuration | does not automatically create external PV actions | none | controller-setting domains | PV/DER bindings and control settings | generally `INIT_ONLY` |
| `SwtControl` | native switch-controller state/config | physical branch action remains a circuit-element command | none | controller setting/state domain | switched-object binding, timing/normal-state settings | generally `INIT_ONLY` |
| `StorageController` | native-controller state/config | does not replace physical Storage dispatch endpoint | none | controller-setting domains | monitored element, schedule/settings, storage bindings | generally `INIT_ONLY` |
| `GenDispatcher` | native-controller state/config | does not automatically replace Generator physical dispatch | none | controller-setting domains | monitored element/generator bindings and settings | generally `INIT_ONLY` |
| `ESPVLControl` | native-control state/configuration | no automatic external plant action | none | controller-setting domains | coordinated resource/control bindings | generally `INIT_ONLY` |
| `UPFCControl` | native-control state/configuration | no automatic external plant action | none | controller-setting domains | UPFC bindings/settings | generally `INIT_ONLY` |
| `Relay` / `Recloser` / `Fuse` | protection status/readout when exposed | no normal external controller action in A03 v1 | future fault/outage/event drivers affect plant elsewhere | protection operating domains | settings and monitored/protected bindings | settings `INIT_ONLY`; event effects later |

## 3. Physical endpoint rule

When a native controller manages a physical device, A03 distinguishes:

```text
controller configuration
        vs
physical plant endpoint
```

Examples:

```text
RegControl.RC1.VReg
    -> native-controller configuration / parameter semantics

Transformer.Reg1 tap command
    -> physical external action endpoint when supported
```

and:

```text
CapControl.CC1 settings
    -> native-controller configuration

Capacitor.Cap1 state command
    -> physical external action endpoint
```

## 4. P1 implications

P1 currently requires generalized support for:

- bus/phase voltage state;
- regulator/tap state/action capability;
- capacitor state/action capability;
- PV P/Q state;
- PV reactive action capability;
- load P/Q disturbance semantics;
- PV active availability disturbance semantics;
- inverter rating/capability metadata.

A03 exposes these generally. The later P1 `ProblemSpec` selects its exact channels.

The following are explicitly **not** A03-global policies:

- exactly ten regulator channels;
- exactly ten capacitor channels;
- exactly ten PV channels;
- the `0.95–1.05 p.u.` P1 voltage operating band;
- P1 stage-cost weights.

## 5. P2 implications

A03 must provide generalized semantics for:

- topology/connectivity readout;
- switchable branch commands;
- source/load/bus identities;
- intrinsic switch/device domains.

P2 fault/outage/event execution and exact feasibility/problem requirements remain later
stages because the P2 science contract is not yet frozen.

## 6. Conservative default

If the A03 policy cannot justify a quantity as a normal per-step external control endpoint,
it must **not** be classified `STEP_CONTROLLABLE`.

Policy extension requires a version/hash change and registry rebuild.
