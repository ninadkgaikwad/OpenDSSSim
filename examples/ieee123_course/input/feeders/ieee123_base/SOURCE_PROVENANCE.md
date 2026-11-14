# IEEE-123 Source Provenance

Installed by: OpenDSSSim_PESGM2027_IEEE123_BaselineBootstrap_v01R3_20261012
Installed UTC: 2026-10-12T22:54:07.1740419Z

Source:
- OpenDSS IEEE PES 123-bus test case
- Public mirror: https://github.com/tshort/OpenDSS
- Source subtree: Distrib/IEEETestCases/123Bus
- License source: repository-root License.txt

Bootstrap history:
- R1: failed before repo mutation because Buscoords.dat URL was invalid.
- R2: fetched all intended R2 source files but failed before repo mutation because a semantic gate used exact whitespace-sensitive string matching.
- R3: semantic gates are case-insensitive and whitespace-tolerant, consistent with OpenDSS command semantics.

Policy:
- ieee123_base is immutable provenance/source evidence.
- ieee123_pesgm2027 is the single shared P1/P2 experiment working copy.
- Later feeder changes must be additive and provenance-recorded.
- Generalized controller source must not hard-code IEEE-123 object names.

Retrieved files:
- IEEE123Master.dss: https://raw.githubusercontent.com/tshort/OpenDSS/master/Distrib/IEEETestCases/123Bus/IEEE123Master.dss
- IEEE123Loads.DSS: https://raw.githubusercontent.com/tshort/OpenDSS/master/Distrib/IEEETestCases/123Bus/IEEE123Loads.DSS
- IEEE123Regulators.DSS: https://raw.githubusercontent.com/tshort/OpenDSS/master/Distrib/IEEETestCases/123Bus/IEEE123Regulators.DSS
- IEEELineCodes.DSS: https://raw.githubusercontent.com/tshort/OpenDSS/master/Distrib/IEEETestCases/123Bus/IEEELineCodes.DSS
- Run_IEEE123Bus.DSS: https://raw.githubusercontent.com/tshort/OpenDSS/master/Distrib/IEEETestCases/123Bus/Run_IEEE123Bus.DSS
- OpenDSS_License.txt: https://raw.githubusercontent.com/tshort/OpenDSS/master/License.txt
