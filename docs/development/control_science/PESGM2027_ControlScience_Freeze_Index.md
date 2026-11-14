# PESGM-2027 Controller-Science Freeze Index

## P1 — Volt/VAR + DER
Authoritative ratified P1 contract (existing repository artifact):

`docs/development/control_science/P1_volt_var_der/P1_VoltVAR_DER_ControlScience_FROZEN.tex`

P1 status: mathematics ratified; IEEE-123 + 10-PV physical augmentation separately qualified.

## P2 — Reconfiguration/Restoration
Authoritative ratified P2 contract installed by this patch:

`docs/development/control_science/P2_reconfiguration_restoration/P2_Reconfiguration_Restoration_ControlScience_FROZEN.tex`

P2 status: Blocks 1--11 frozen for implementation.

## Implementation boundary now authorized
The next development stage may implement controller classes for P1/P2 plus the
controller-side orchestration/model layer. Implementations must preserve:

- no controller mutation of AltDSS;
- `env.step(a_req)` as authoritative physical mutation boundary;
- controller-side model/topology/forecast services;
- common requested/applied/realized audit;
- last-successful-control memory in each controller;
- no hard-coded IEEE-123 object IDs in generalized controller source.

P2 experiment-feeder construction remains a separate post-math-freeze task.
