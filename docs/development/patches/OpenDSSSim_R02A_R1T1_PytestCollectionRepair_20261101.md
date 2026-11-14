# R02A-R1T1 pytest collection repair — 2026-11-01

## Scope and evidence

- Exact predecessor: installed, unqualified R02A-R1 224-file manifest SHA-256 `76046C34083F1E9A6BB700B228A5EA8C82DA383CB2DBCA0E112B4B68DF458394`.
- Original targeted qualification failed at collection (`pytest` exit code 2): `request` is a reserved name and cannot be used in `@pytest.mark.parametrize`.
- Change: rename the parametrized test argument from `request` to `object_ref` and its two internal references, with no altered assertions or native runtime logic.
- Other than this test, add this traceability note; **no backend, A03/A04/A05I2, fixture, or feeder changes**.
- Maintain R01 and R02 as open. R02A/R02A-R1 prior failed results are retained; requalification must pass targeted and three independent fresh-process full suites.

## Authorization / freeze

This is a test infrastructure repair only. It does not resolve R01 or establish that R02 is fixed. It does not authorize A05I3 until independent native evidence is reviewed and A05I2 is qualified.
