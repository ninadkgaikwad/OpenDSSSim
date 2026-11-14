# P2 Stage 3 — Electrical feasibility *screening* V01

This adds a **read-only research/audit harness** and **does not modify** any existing feeder, `src/opendsssim` runtime, existing P2 science, or any controllers.

- Independent AltDSS context for every test case and demand multiplier
- 7 prequalified topological cases × [0.60, 0.80, 1.00, 1.20, 1.40] demand factors = 35 native AC snapshots
- Per-bus/per-phase p.u. voltages, per-line/per-conductor amperes, per-load realized kW
- CSV + JSON + Markdown reports and independent SHA256 receipt under a user-supplied external evidence folder
- Pinned input SHA256 verification before any native solve
- **No native ampacity ratings are accepted as authoritative unless separately specified with engineering provenance**
- Tie lines are provisional low-impedance placeholders: physical line lengths/conductors/ampacities still to be engineered

## Run (from OpenDSSSim repository root)

```powershell
python -B experiments/pesgm2027/p2_restoration/electrical_screen_v01/validate_stage3_static.py
$Evidence = Join-Path $HOME 'Downloads\P2_Stage3_ElectricalScreen_V01'
python -B experiments/pesgm2027/p2_restoration/electrical_screen_v01/run_stage3_electrical_screen.py --out $Evidence
```

If ratings become available from trustworthy engineering records, provide an optional CSV with columns `line,normal_amps`. Partial rating coverage remains **THERMAL_NOT_ASSESSABLE**; a rating in a DSS engine inherited default is not a defensible conductor or switch ampacity.

**Interpretation**: A converged power flow is not necessarily voltage-feasible, thermally feasible, or physically realizable. The 0.95–1.05 p.u. comparison band and load multipliers are illustrative, not ratified official experiment numerics. The current survey does not model protection-clearing sequences, faults as short circuits, or the official `env.step` controller interface.

### Outputs

- `STAGE3_SUMMARY.csv`: configuration × demand level metrics
- `STAGE3_BUS_PHASE_VOLTAGES.csv`: node-level voltage values and exploratory band flags
- `STAGE3_LINE_PHASE_CURRENTS.csv`: line terminal/phase current magnitudes and any explicitly supplied ratings
- `STAGE3_LOAD_REALIZATION.csv`: individual load terminal-voltage and realized kW readings
- `STAGE3_RECEIPT.json`: source hashes, run completeness and missing qualification gates
- `STAGE3_README.md`: summary for review
- `STAGE3_OUTPUT_SHA256.json`: evidence-file hash registry

The user should upload the entire evidence directory as a ZIP when complete (or the summary, receipt, and top overloaded/undervoltage rows if upload size constrained). Do not treat PASS_MEASUREMENT as full AC-feasibility PASS.
