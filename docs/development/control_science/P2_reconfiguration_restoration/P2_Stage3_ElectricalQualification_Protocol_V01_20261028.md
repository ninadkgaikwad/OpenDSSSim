# P2-MF01/MF02 — Stage 3 native electrical qualification protocol V01

Date: October 28, 2026. **Status: research screening protocol, not an electrical-feasibility certificate or a change to ratified controller science.**

## 1. Inputs and frozen architecture

This protocol measures the previously ratified simple and exotic P2 IEEE-123 circuits. Both are independently compiled by AltDSS for each test. Original IEEE-123, P1 feeder, and existing P2 reference copies remain unchanged. Faulted devices are pre-isolated as standalone fixture setup. The actual OpenDSSSim `env.step` boundary remains authoritative during future controller comparisons.

The preceding native-smoke evidence (`P2_RATIFIED_FEEDER_NATIVE_SOLVES_V01.json`) contains convergence results for seven valid cases and structural rejection of MF02_INVALID, but no electrical voltages, branch loading or feeder ampacity evidence.

## 2. Study matrix

| Case | Purpose |
|---|---|
| MF01_PRE | Four health-down devices, no restoration |
| MF01_RESTORED | Four health-down, Sw8/Sw9 restoration |
| MF02_PRE | Three line health-down, no restoration |
| MF02_SW7_SW8 | Partial restoration using existing ties |
| MF02_A | Full connectivity via Sw9 |
| MF02_B | Full connectivity via Sw10 |
| MF02_C | Full connectivity with Sw9/Sw10 and Sw11 sectionalizer open |

Each case is independently solved at illustrative demand multipliers 0.60, 0.80, 1.00, 1.20, and 1.40. The same multiplier is applied to all eligible source-defined loads, and different native load models may draw different power as voltages vary. This is a 35-snapshot stress **screen**, not a time-series controller experiment.

## 3. Native measurement outputs

1. Bus/node/phase p.u. voltages, minima/maxima, exploratory 0.95/1.05-p.u. excursions, near-zero node counts.
2. Phase and terminal-specific line current magnitudes in amperes.
3. Native load terminal voltage indicators and measured real consumption, separated from topology-based nominal connected kW.
4. Source power and information on missing or user-supplied ratings.
5. Full run provenance, input hashes, all failures, and reproducible output-file hashes.

### Interpretability and limits

- A zero-voltage node is **not automatically** a proof of a fault or unserved source connectivity; independent graph/health checks are still needed.
- Operating-voltage screening bounds are **illustrative** and do not silently amend the frozen P2 contract.
- No conductor ampacity or switch normal/short-duration ratings appear in these frozen IEEE-123 DSS files. OpenDSS inherited/default `NormAmps` may be reported for diagnostics, but must **not** be used to assert thermal feasibility.
- Sw7–Sw10 have placeholder short/low-impedance representations, not engineered route lengths, conductor choices, or switch ratings. A voltage/flow difference between A/B/C under these placeholders is an exploratory result only.
- Native regulator/capacitor controls remain as compiled in each circuit. No controller-specific reconfiguration or `env.step` exercise is performed here.
- `MF02_INVALID` is rejected structurally before native solve.

## 4. Evidence and decision gates

**Screen measurement PASS** requires pinned sources, the expected case set, and successfully extracted finite native voltage/current/load measurements for all 35 snapshots. One or more observed voltage excursions are recorded as real screening findings, not silently ignored. Incomplete solves or extraction failures lead to a FAIL receipt.

**Physical-operational feasibility** cannot be marked PASS until each proposed tie has engineering-grade impedance/length/ampacity, original feeder line ampacity provenance, and agreed actual operating limits. After these inputs are ratified, rerun common load trajectories and compare MF02 A/B/C per-phase voltage and branch loading. Only then freeze the experiment's priorities, curtailability, timestep and evaluation horizon.

This protocol produces no new controller implementation and respects the OpenDSSSim v1 implementation hold point.
