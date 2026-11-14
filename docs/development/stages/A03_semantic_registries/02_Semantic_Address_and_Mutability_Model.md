# A03.2 — Semantic Address and Mutability Model

## 1. Why an address model is required

Not every meaningful OpenDSSSim quantity is a writable DSS property.

Examples:

- `PVSystem.PV1.kvar` is naturally addressed as a native property;
- bus voltage is a solved runtime readout;
- opening/closing a switchable circuit element may be expressed as a circuit-element
  operation rather than a fabricated property.

A03 therefore freezes three address families.

## 2. `NativePropertyAddress`

Represents a canonical OpenDSS object/property identity.

Conceptual form:

```text
NativePropertyAddress(
    object_full_name="PVSystem.PV1",
    property_name="kvar"
)
```

Examples:

```text
PVSystem.PV1.kvar
Storage.BESS1.kW
Storage.BESS1.kvar
Capacitor.Cap1.States
RegControl.RC1.VReg
Line.L1.NormAmps
```

A native property address does not imply mutability or registry membership by itself.

## 3. `RuntimeReadoutAddress`

Represents a solved/read-only service channel whose physical meaning is not accurately
represented as an editable DSS property.

Conceptual form:

```text
RuntimeReadoutAddress(
    service="Bus",
    entity="bus17",
    channel="pu_voltage"
)
```

Examples:

```text
Bus.<name>.voltage
Bus.<name>.pu_voltage
CircuitElement.<name>.currents
CircuitElement.<name>.terminal_power
CircuitElement.<name>.losses
Solution.converged
Topology.connectivity
```

The exact implementation channel names are frozen by A03 code/schema, not by paper
configuration.

## 4. `RuntimeCommandAddress`

Represents a legitimate plant-owned command/operation that should not be modeled as a
made-up DSS property.

Conceptual form:

```text
RuntimeCommandAddress(
    service="CircuitElement",
    entity="Line.SW1",
    operation="open_close"
)
```

Examples include:

- branch open/close;
- transformer/regulator tap movement where the plant semantic is an operation;
- other future plant commands that have explicit backend semantics.

A runtime command is still subject to `STEP_CONTROLLABLE` policy and future `ProblemSpec`
authorization.

## 5. Address identity

Every semantic entry must have deterministic identity derived from:

- address family;
- native entity/service;
- native property/channel/operation;
- terminal/phase/winding/selectors when required;
- quantity identity.

The semantic layer must preserve native object names rather than replacing them with
paper-specific aliases.

## 6. Mutability classes

A03 freezes four OpenDSSSim semantic mutability classes.

### `READ_ONLY`

The quantity may be observed/read but not changed through the normal simulator semantic
control interface.

Examples:

- solved bus voltage;
- element current;
- solution convergence;
- structural/topological identity.

### `INIT_ONLY`

The quantity is configuration/parameter metadata that may be set during model/circuit
construction or controlled setup but is not a normal per-step controller action.

Examples can include:

- ratings/configuration;
- native controller configuration;
- network electrical parameters.

Raw AltDSS setter availability does not override this classification.

### `STEP_CONTROLLABLE`

The quantity/operation is a legitimate per-step external plant-control endpoint.

Examples:

- PV reactive-power command;
- storage active/reactive dispatch;
- capacitor state command;
- tap command/movement;
- switch open/close.

A `STEP_CONTROLLABLE` entry may still be excluded from a particular `ProblemSpec`.

### `STEP_EXOGENOUS`

The quantity changes with time through the exogenous plant-input path rather than through
controller action.

Examples:

- load active/reactive demand;
- PV active-power availability;
- outage/event drivers when such execution is introduced later.

A03 defines the semantic role only; A05+ executes the time-series/event progression.

## 7. Setter availability is not semantic authority

The following inference is forbidden:

```text
AltDSS property has setter
        ->
STEP_CONTROLLABLE
```

A property becomes externally controllable only through the explicit class-by-class A03
semantic policy.

## 8. Static definition vs live value

Registries persist:

- semantic ID;
- address;
- quantity/unit/type/shape metadata;
- selectors;
- mutability;
- static rating/domain metadata;
- relationships/capability tags.

Registries do not persist the current episode's voltage, power, tap, SOC, switch state,
convergence, or realized command as semantic truth.

## 9. Canonical semantic entry

The implementation should use one canonical definition conceptually equivalent to:

```text
SemanticEntry
    semantic_id
    address
    native_entity
    quantity
    unit
    dtype
    shape
    selectors
    mutability
    static_metadata
    capability_tags
```

The seven registries are typed/indexed views over canonical entries rather than seven
unrelated copies of the same semantics.
