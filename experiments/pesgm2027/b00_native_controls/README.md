# B00I1 native-as-installed pilot

Use `python -B experiments/pesgm2027/b00_native_controls/run_b00.py --repo-root <repo> --output-root <new external directory> --feeder all --steps 3` with the qualified environment. The script creates only out-of-repository results, reads four existing masters unchanged, and uses qualified A05 file replay plus the native A04 snapshot path.

Default curves `load=[0.75,1.00,1.15]`, `PV irradiance=[0.0,0.8,1.0] kW/m2` are **synthetic diagnostic fixtures**, not actual utility load/weather. Reset and first step both solve the initial sample by A05I3 clock design. The final step uses the last sample and truncates. For B00I1, P2 MF01/MF02 are PRE health/topology only, no switching or restoration.

The instrumented H2 run reports tap/cap state status from trusted A05 history, but native `ControlMode`, `RegControl.Enabled`, control queue, and total loss telemetry are not fully available through the controller-facing public API. Do **not** mistake a pilot pass for the final B00 common-comparison freeze.

For the original A05 V1 source freeze, the qualified files are unchanged. New B00 science files must be independently qualified. Never run the installer twice after a partial failure.
