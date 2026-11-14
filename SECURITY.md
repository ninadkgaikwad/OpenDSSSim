# Security and operational scope

OpenDSSSim is research software, not an operational protection, SCADA, or switching control system. The native simulator and the included RBC/MPC policies have not been audited as safety-critical grid software.

Report potential security issues privately to the repository maintainers via GitHub's private vulnerability-reporting feature when enabled. Do not post credentials, customer infrastructure, private equipment locations, or exploit material in a public issue. The project does not currently advertise a formal security support SLA.

The example runner checks inputs, refuses output overwrite and uses public action contracts. These protections are research reproducibility safeguards; they are not a substitute for deployment isolation or operational authorization.
