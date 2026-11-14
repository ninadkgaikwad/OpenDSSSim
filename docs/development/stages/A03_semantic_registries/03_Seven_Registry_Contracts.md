# A03.3 — Seven Registry Contracts

## 1. Common design rule

The seven registries are persistent typed views over canonical semantic definitions. They
are allowed to reference the same underlying physical quantity for different semantic
purposes without duplicating inconsistent definitions.

## 2. `CircuitRegistry`

### Question

> What native entities and structural/control relationships exist in the circuit?

### Sources

Primarily the A02H1 `CircuitInventory`.

### Contains

- native full object names and DSS classes;
- bus/node identities;
- phase/terminal/conductor structure;
- terminal bus specifications;
- structural entity selectors;
- native controller objects;
- controller relationships:
  `CONTROLS`, `MONITORS`, `MONITORS_BUS`, `SWITCHES`, `PROTECTS`,
  `COORDINATES_CONTROL`.

### Does not contain

- live solved values;
- problem-selected action/observation subsets.

## 3. `StateRegistry`

### Question

> What current plant quantities can the simulator read as generalized physical/runtime
> state?

### Examples

- bus/phase voltages;
- element currents and terminal powers;
- transformer tap realization;
- capacitor realization;
- switch realization;
- PV/storage/generator realized operating points;
- storage energy/SOC where supported;
- solution convergence;
- topology/connectivity readouts.

### Boundary

`StateRegistry != ObservationSpace`.

## 4. `ActionRegistry`

### Question

> What legitimate plant commands could external control request under generalized
> OpenDSSSim semantics?

### Examples

- PV inverter reactive-power request;
- storage active/reactive dispatch;
- capacitor state command;
- regulator/tap command;
- switch open/close;
- explicit generator dispatch only when semantic policy supports it.

### Boundary

- action capability does not imply selection by every problem;
- native controller settings are not automatically physical external actions;
- writable property does not imply action.

## 5. `DisturbanceRegistry`

### Question

> What time-varying quantities are exogenous to controller action?

### Examples

- load active demand;
- load reactive demand;
- PV active-power availability;
- future outage/fault/event drivers.

### Mutability

Typically `STEP_EXOGENOUS`.

### Boundary

A03 does not execute disturbance profiles. It only defines semantic channels.

## 6. `ConstraintRegistry`

### Question

> What intrinsic plant/device domains or limits are available for later validation,
> admissibility, modeling, or optimization?

### Examples

- inverter kVA/reactive capability metadata;
- storage ratings/energy bounds;
- tap min/max/discrete domain;
- capacitor discrete states;
- line normal/emergency ampacity;
- switch allowed states.

### Boundary

Problem-specific requirements remain later `ProblemSpec` content.

For example, P1's voltage band is not globally baked into A03.

## 7. `ParameterRegistry`

### Question

> What static/configuration quantities characterize the circuit/device but are not normal
> per-step controller actions?

### Examples

- voltage/current/power ratings;
- line length/impedance data;
- transformer winding ratings/configuration;
- PV `Pmpp`/kVA configuration;
- storage kW/kWh/kVA ratings;
- native controller setpoints, bands, delays, and bindings where classified as
  configuration.

### Typical mutability

`READ_ONLY` or `INIT_ONLY`.

## 8. `CapabilityRegistry`

### Question

> What higher-level services and generalized physical/control abilities does this circuit
> support?

### Example capability families

```text
observation.bus_voltage
observation.element_current
observation.element_power
control.pv_reactive_power
control.storage_active_power
control.storage_reactive_power
control.capacitor_switching
control.regulator_tap
control.branch_switching
native_control.regulator
native_control.capacitor
native_control.inverter
service.topology
service.snapshot_solve
constraint.ampacity
constraint.inverter_capability
constraint.tap_bounds
```

Capability names are implementation vocabulary for machine-queryable semantics, not
replacement names for OpenDSS objects.

## 9. Registry overlap

A physical fact may support more than one registry view.

Example:

```text
PVSystem.PV1.kVA
```

can be:

- a `ParameterRegistry` rating;
- metadata used by an inverter capability entry in `ConstraintRegistry`;
- evidence supporting a higher-level inverter capability in `CapabilityRegistry`.

The canonical address/definition remains singular.

## 10. Stable ordering and identity

All registry outputs must use deterministic ordering and semantic IDs so equivalent circuit
inventories/policies produce the same semantic bundle hash.
