# P2 ratified simple/exotic IEEE-123 feeder variants

Both feeders are stored under `experiments/pesgm2027/feeders/` as independent copies. The original eight-switch P2 feeder, original IEEE-123 and P1 feeder remain unchanged.

- `ieee123_p2_mf01_simple/IEEE123Master.dss`: 9 switch controls, four health-down elements on the scenario fixture.
- `ieee123_p2_mf02_exotic/IEEE123Master.dss`: 11 switch controls, three health-down lines; routes A/B/C.
- `P2_RATIFIED_TWO_SCENARIOS_V01.json`: ratification contract.
- `P2_RATIFIED_STATIC_CASES_V01.json`: pre-isolated standalone scenario fixture.
- `topology_snapshot_qualified_v02.json`: pinned graph parity reference, **not** native electrical simulation.
- `validate_p2_ratified_design_static.py`: reproducibility and static structural counts, no external Python packages.
- `validate_p2_ratified_design_altdss.py`: optional independent native AltDSS compile/solve qualification; requires the correct `altdss` environment.

Run from repository root:

```powershell
python -B experiments/pesgm2027/p2_restoration/ratified_design_v01/validate_p2_ratified_design_static.py
$Evidence = Join-Path $HOME 'Downloads\P2_IEEE123_Ratified_NativeQualification_V01'
python -B experiments/pesgm2027/p2_restoration/ratified_design_v01/validate_p2_ratified_design_altdss.py --out $Evidence
```

The scenario fixture is **not** a controller and its direct AltDSS commands must never be used to mutate the official OpenDSSSim plant. Health/fault state must come through authoritative plant state in later controller evaluations.

**Design ratified; electrical parameters and AC feasibility pending.**
