# IEEE123 diagram coordinates

- Dataset: BusCoords.dat in PauloRadatz/opendss-python-examples/feeder_models/IEEETestCases/123Bus.
- Public source URL: https://raw.githubusercontent.com/PauloRadatz/opendss-python-examples/main/feeder_models/IEEETestCases/123Bus/BusCoords.dat
- Source lines: 130. Captured from public source 2026-11-12; this CSV is plotting metadata only.
- `x,y` are arbitrary feeder-diagram coordinates, **NOT geographic longitude/latitude or surveyed asset locations**.
- The qualified OpenDSSSim repository tree did NOT contain IEEE123 Buscoords.dat. These coordinates must NOT be injected into the physical feeder or mistaken for measured geospatial data.
- Extra experimental nodes, including MF02 `p2sw11mid`, have derived illustrative coordinates with explicit `coordinate_provenance=derived_layout`.
- Source topology and switch entities come from checksum-pinned OpenDSSSim MPC static case data, not from the public layout reference.
