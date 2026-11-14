# A03.7 — Capability and Controller Compatibility

## 1. Capability hierarchy

A03 freezes:

```text
engine capabilities
      >=
circuit capabilities
      >=
problem-required capabilities
```

The engine may support a class/operation that is absent from a given circuit.

The circuit may expose a capability that a particular problem does not select.

## 2. Capability purpose

Capabilities provide a compact machine-queryable answer to questions such as:

- can bus voltage be observed?
- does the circuit contain externally controllable PV reactive-power endpoints?
- are switchable branches present?
- is topology readout available?
- do native regulator controls exist?
- are intrinsic inverter/tap/ampacity limit semantics available?

## 3. Compatibility with generalized controllers

The controller-science contract requires controller requirements to be declared explicitly.

A future compatibility resolver should compare:

```text
ControllerRequirements
        vs
ProblemSpec + CapabilityRegistry
```

and produce exactly one of:

```text
SUPPORTED
UNSUPPORTED
```

`UNSUPPORTED` must identify missing requirement IDs and diagnostics.

No silent substitution/degradation is permitted.

## 4. A03 responsibility

A03 provides:

- machine-readable circuit/native-object registry;
- capability query metadata;
- semantic IDs/addresses needed for later binding;
- enough information for explicit missing-capability diagnostics.

A03 does not yet instantiate controllers or freeze final compatibility APIs.

## 5. Native controls as capabilities

Native controller presence can advertise capabilities such as:

```text
native_control.regulator
native_control.capacitor
native_control.inverter
```

These describe circuit capability, not external authority.

A later authority layer decides whether native control or external OpenDSSSim control is
active for a device/problem.

## 6. P1 examples

P1 may later require capability IDs equivalent in meaning to:

```text
observation.bus_voltage
control.regulator_tap
control.capacitor_switching
control.pv_reactive_power
constraint.inverter_capability
```

The exact P1 selected device objects remain experiment/`ProblemSpec` configuration.

## 7. P2 examples

The P2 scaffold indicates likely future requirements including:

```text
service.topology
observation.connectivity
control.branch_switching
```

plus source/load/event/feasibility capabilities once P2 science is frozen.

A03 must not pre-emptively freeze P2 benchmark-specific details that the controller-science
documents explicitly leave open.
