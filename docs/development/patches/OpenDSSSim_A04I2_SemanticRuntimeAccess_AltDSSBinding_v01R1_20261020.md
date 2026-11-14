# OpenDSSSim A04I2 - Semantic Runtime Access + AltDSS Binding

**Patch ID:** `OpenDSSSim_A04I2_SemanticRuntimeAccess_AltDSSBinding_v01R1_20261020`  
**Date:** 2026-10-20  
**Status:** SOURCE IMPLEMENTATION CANDIDATE PENDING INDEPENDENT QUALIFICATION

## Predecessor Authority

A04I2 installs only on the independently qualified A04I1 authority:

```text
Repository files: 166
Qualified source-manifest SHA256:
4E6717ABE4D00ECD74EA77779EC9322D7CBA4FF141025BD8F6AD7FFD4D3B41FA
```

## Scope

A04I2 implements the mechanism-only execution layer for already-frozen A03 semantic addresses.

It adds:

```text
src/opendsssim/runtime/access.py
```

and narrowly extends the backend contract and AltDSS backend with:

```text
write_object_property(...)
read_runtime_channel(...)
apply_runtime_command(...)
```

A04I2 does **not** implement ProblemRuntimeBinding, control-authority policy, fault scheduling, environment `step()` integration, history, preflight caching, or A05 temporal/exogenous profiles. Those remain A04I3/A05 scope.

## A03 Immutability

The A03 semantic source is immutable in this patch:

```text
src/opendsssim/semantics/schema.py
src/opendsssim/semantics/compiler.py
src/opendsssim/semantics/policy.py
src/opendsssim/semantics/__init__.py
```

A04I2 executes the existing address families without changing their meaning:

```text
NativePropertyAddress
RuntimeReadoutAddress
RuntimeCommandAddress
```

## Native Property Access

`NativePropertyAddress` is executed through exact native class/object/property identity.

Writes use the AltDSS object-edit interface and return authoritative post-write readback.

No broad object rediscovery, silent property substitution, or controller authorization is performed here.

Representative qualification includes:

- PVSystem `kvar` read/write;
- `Enabled=False` and restoration;
- case-insensitive exact native property lookup.

## Runtime Readouts

A04I2 binds the A03 runtime-readout vocabulary:

### Bus

```text
Bus / <bus> / voltage
    -> complex native node-voltage tuple

Bus / <bus> / pu_voltage
    -> float per-unit voltage-magnitude tuple
```

### CircuitElement

```text
currents
    -> complex conductor/terminal current tuple

terminal_power
    -> complex total-power-per-terminal tuple

losses
    -> complex total element loss

open_state
    -> boolean tuple, one entry per terminal
```

### Transformer / AutoTrans

```text
taps
    -> float tuple, one entry per winding
```

### Solution

```text
converged
    -> bool
```

### Topology

```text
connectivity
    -> deterministic topology-status mapping containing isolated branches,
       isolated loads, looped pairs, and associated counts
```

## Runtime Commands

### Transformer / AutoTrans `set_tap`

The scalar A03 tap command targets the unique RegControl tap winding associated with the transformer/autotransformer.

A04I2 fails closed unless exactly one controlled tap winding can be resolved.

The command:

1. reads the current native `Taps` array;
2. modifies only the controlled tap winding;
3. writes the complete native `Taps` array;
4. returns authoritative tap readback.

Authority suppression itself remains A04I3 scope. Genuine A04I2 qualification therefore explicitly disables the fixture RegControl before commanding the external tap and verifies persistence through a subsequent solve.

### CircuitElement `open_close`

The A03 branch-switch command resolves the associated `SwtControl.SwitchedTerm` when one exists; an explicitly switchable line without a SwtControl uses terminal 1. The operation always applies to all conductors of the resolved terminal:

```text
OPEN   -> element.Open(resolved_terminal, 0)
CLOSED -> element.Close(resolved_terminal, 0)
```

Conflicting multiple SwtControl terminals fail closed.

The command accepts canonical semantic values `OPEN` / `CLOSED` and also 0 / 1 for later lossless Gym-domain decoding.

A04I2 qualification explicitly disables the fixture SwtControl before external switching. General authority ownership remains A04I3 scope.

## Runtime Access Boundary

`SemanticRuntimeAccess` is deliberately mechanism-only:

```text
read(NativePropertyAddress)
read(RuntimeReadoutAddress)
write(NativePropertyAddress, value)
write(RuntimeCommandAddress, value)
```

It rejects:

- reading a `RuntimeCommandAddress`;
- writing a `RuntimeReadoutAddress`.

It does not decide whether a ProblemSpec authorizes a given action. That is A04I3 runtime-binding responsibility.

## Genuine Qualification

A04I2 qualification must execute against the real AltDSS 0.2.4 backend and existing `a03_semantic` fixture, covering:

1. native property read/write;
2. `Enabled=False` readback;
3. bus voltage and pu-voltage readouts;
4. circuit-element currents, terminal power, losses, and open-state readouts;
5. transformer tap readout;
6. external tap command with native RegControl disabled;
7. open/close command with native SwtControl disabled;
8. solution and topology readouts;
9. persistent context identity through runtime accesses/commands;
10. fail-closed unsupported runtime vocabulary;
11. full A01-A04I1 regression;
12. A03 standalone validator;
13. byte identity of all A03 semantic source.

## Expected Repository Transition

```text
166 qualified A04I1 files
+ 7 additive A04I2 files
= 173 files
```

Modified predecessor files are limited to:

```text
pyproject.toml
src/opendsssim/__init__.py
src/opendsssim/backends/base.py
src/opendsssim/backends/altdss_backend.py
```

## Next Gate

A04I3 - Runtime Binding + Environment + History + Preflight is authorized only after A04I2 independently qualifies.
