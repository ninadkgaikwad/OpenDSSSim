# A04I4A switching-authority amendment — fresh directed-source v02

## Source of truth

Built strictly from the 93-file user-provided directed input ZIP
`OpenDSSSim_A04I4A_DIRECTED_INPUT_V01R1_20261022_153058.zip`, SHA256
`4C8C8D45DCFB170D81ABA73E3AB0843E5401CEDB2B9440027CC81A71FFDCDB8A`.
Collector established byte identity for all 191 predecessor files against
A04I4 qualified manifest SHA256 `D93D7B6BEB4A1645AED052E59863DCC2C00CF06917930E9583DEDFBDAA8344C0`.

## Scope

The only production change is `src/opendsssim/runtime/binding.py`.
A02H1 native-control discovery vocabulary and A03 semantic registries are unchanged.
A04I2 AltDSS runtime access and circuit source identity are unchanged.
SwtControl SWITCHES grants exclusive authority to an externally controlled line
**only** when native source class/object, `SwitchedObj`, target resolution,
line identity, and terminal range are verified. The matching SwtControl
must advertise `Enabled`, and suppression is verified after reset and solve.
`MONITORS`, `PROTECTS`, and other roles are non-owning. Unresolved SwtControl
references with external lines, malformed relations, and HYBRID controller
partition conflicts fail before control writes.

## Test fixture correction

The earlier v01R1 generated inventory/preflight caches inside the source root,
causing the frozen CircuitSource full-tree hash to change before second reset.
The new genuine AltDSS test copies the circuit into `tmp/circuit_source` and
puts all generated state into a distinct sibling `tmp/generated_state`.
Do not relax the conservative source-tree contract.

## Controlled changes

Four modified files: runtime binding, A04I3 standalone validator, A04I3
switch-integration regression, and A04I4 behavioral test. Four additions:
policy unit tests, isolated real AltDSS switching integration, successor
standalone validator, and this documentation.

## Qualification

Installer requires exact 191-file baseline and 8-member payload, executes
unit + genuine AltDSS integration checks, and rolls back if any gate fails.
Independent validator runs full pytest, A03, A04I2 (only existing
package_version exception), A04I3 successor, A04I4 successor and this A04I4A
standalone plus source freeze gate. A new 195-file source SHA is only
qualified on laptop PASS.

## Deferred boundaries

A05 temporal profiles, physical P2 reconfiguration feasibility, radiality,
protection coordination and line-switching interlocks remain separately scoped.
