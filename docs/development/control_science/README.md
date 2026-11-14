# OpenDSSSim Control-Science Development

**Track:** PESGM 2027 generalized-controller science  
**Status:** C0A DOCUMENTATION SCAFFOLD — NO CONTROLLER IMPLEMENTATION  
**Patch:** `OpenDSSSim_ControllerScience_C0A_DocumentationScaffold_v01R3_20261005`

## Purpose

This directory is the authoritative repository home for literature-backed controller
science, mathematical contracts, capability requirements, fair-comparison rules,
reproducibility/provenance, and the mapping from controller formulations to frozen
OpenDSSSim interfaces.

Control science is developed in parallel with the generalized simulator, but controllers
are not allowed to bypass or redefine the OpenDSSSim plant boundary.

## Ownership boundary

The controller-science track owns:

- full-text literature audit;
- common P1/P2 physical-control problem definitions;
- controller mathematics;
- objective/reward definitions;
- capability requirements and unsupported-circuit semantics;
- fair-comparison/information contracts;
- tuning/training/calibration protocols;
- controller-specific diagnostics;
- generalized controller software contracts after the science freezes;
- later controller implementation against frozen OpenDSSSim abstractions.

The simulator track owns:

- AltDSS backend/plant;
- circuit and capability discovery;
- native registries;
- `ProblemSpec`;
- Gymnasium spaces and lifecycle;
- external time-series execution;
- requested/applied/realized action semantics;
- physical action realization and snapshot solve;
- parity, replay, history, persistence, performance, and qualification.

**Controller source must never import or directly manipulate AltDSS, issue DSS commands,
or mutate backend objects.**

The controller emits only a requested action \(a_{\mathrm{req}}\). OpenDSSSim owns
validation/admissibility/projection, \(a_{\mathrm{applied}}\), the physical solve, and
\(a_{\mathrm{realized}}\).

## Generalized-controller rule

A controller is generalized when its implementation can instantiate on any compatible
OpenDSS circuit satisfying its declared capability requirements.

This does **not** mean every controller must operate on every possible circuit.

Missing requirements must yield an explicit machine-readable `UNSUPPORTED` result;
silent degradation is prohibited.

No generalized controller source may hard-code IEEE-123 object names. IEEE-123 device
selection and benchmark modifications belong in experiment configuration.

For RL, the training/evaluation pipeline can be circuit-general even when a fixed trained
checkpoint is not feeder-universal.

## Repository ownership

### Reusable controller science and later reusable implementation

```text
docs/development/control_science/
src/opendsssim/controllers/          # later, after science/software-contract gates
configs/controllers/                 # later reusable controller configuration
```

### Paper-specific validation workloads

```text
experiments/pesgm2027/
    ieee123/
    volt_var_der/
    restoration/
```

IEEE-123 object selections, feeder modifications, campaign settings, trained checkpoints,
and paper-only benchmark choices belong in the experiment layer, not reusable controller
source.

Thus the PESGM controllers remain external validation workloads while reusable controller
classes may still live under `src/opendsssim/controllers/` after the implementation gate.

## Six paper controller paradigms

### P1 — Volt/VAR + DER coordination

- reference/rule;
- optimization/MPC;
- reinforcement learning.

### P2 — Reconfiguration/restoration

- graph/rule reference;
- optimization/MPC;
- reinforcement learning.

The six algorithms are literature-backed baselines/demonstrators. OpenDSSSim does not
claim them as new controller algorithms.

## Status vocabulary

Use these status labels consistently:

- `DRAFT` — active formulation; not safe for implementation.
- `RATIFIED` — scientific decisions agreed but implementation mapping may still be
  incomplete.
- `FROZEN` — literature provenance, mathematics, common information contract, capability
  requirements, and implementation mapping are complete enough to serve as an
  implementation contract.

A controller should not enter production implementation from a `DRAFT` science document.

Files created by C0A are scaffolds. A file is not scientifically frozen merely because
its filename contains `FROZEN`; it becomes frozen only after source audit and explicit
ratification.

## Required record for each controller

Every controller freeze must identify:

1. primary and supporting sources;
2. `REUSE` from literature;
3. `ADAPT` for OpenDSSSim/generalized execution;
4. `NEW` software abstraction, if any;
5. state/observation;
6. disturbance/forecast access;
7. action;
8. constraints;
9. objective/reward;
10. horizon/control interval;
11. solver/RL algorithm;
12. tuning/training/calibration data policy;
13. termination/truncation semantics where relevant;
14. capability requirements;
15. diagnostics;
16. paper metrics;
17. exact mapping to frozen OpenDSSSim interfaces.

## Fair-comparison rule

Within each physical problem, all paradigms must share the same controller-independent:

- feeder;
- time axis;
- disturbances;
- load/PV/weather realization;
- faults/events;
- controllable physical assets;
- physical bounds;
- network constraints;
- common metrics;
- initial conditions;
- control interval;
- available current measurements.

Forecast/information differences must be explicit. No hidden privileged information is
allowed.

## Development sequence

1. **C0 — Literature audit**
   - obtain and audit the six primary controller sources;
   - collect supporting sources only where necessary;
   - preserve exact provenance;
   - record `REUSE` / `ADAPT` / `NEW`.

2. **C1 — Common physical problems**
   - freeze P1 common Volt/VAR + DER physics and information contract;
   - freeze P2 common restoration/reconfiguration physics and information contract;
   - establish fairness before controller-specific equations.

3. **C2 — Freeze P1**
   - reference/rule;
   - optimization/MPC;
   - RL;
   - capabilities, fairness, reproducibility;
   - final frozen P1 TeX contract.

4. **C3 — Freeze P2**
   - graph/rule;
   - optimization/MPC;
   - RL/DQN as selected by source audit;
   - capabilities, fairness, reproducibility;
   - final frozen P2 TeX contract.

5. **C4 — Controller software contract**
   - typed requirements/context/output;
   - controller registry;
   - explicit unsupported semantics;
   - no AltDSS imports.

6. **C5 — Mock implementation**
   - only if simulator A03/A04 are not yet available;
   - mocks must not invent a plant API that bypasses future OpenDSSSim interfaces.

7. **C6 — Real integration**
   - after simulator A03/A04 freeze the required registries and `ProblemSpec`/Gym
     contracts.

## Implementation gate

Controller source under `src/opendsssim/controllers/` should be created only after:

1. the relevant P1/P2 science contract is sufficiently frozen; and
2. the required simulator-side interfaces are frozen.

If simulator support is missing, create an interface requirement for the simulator track.
Do not access AltDSS directly as a workaround.

## Primary synchronization points

- **A02** — capability/circuit discovery;
- **A03** — native registries;
- **A04** — `ProblemSpec` and generalized Gym spaces;
- **A05** — external time-series/forecast execution.

Controller-side requirements discovered during C0-C3 are recorded in:

`common/Simulator_Interface_Requirements.md`

## Directory map

```text
control_science/
    README.md
    common/
        Controller_Science_Architecture.md
        Generalized_Controller_Contract.md
        Capability_Requirements.md
        Fair_Comparison_Contract.md
        Simulator_Interface_Requirements.md
        Notation_and_Native_Vocabulary.tex
    P1_volt_var_der/
        P1_VoltVAR_DER_ControlScience_FROZEN.tex
        P1_Common_Physical_Problem.md
        P1_Reference_Controller.md
        P1_Optimization_Controller.md
        P1_RL_Controller.md
        P1_Implementation_Mapping.md
    P2_restoration/
        P2_Reconfiguration_Restoration_ControlScience_FROZEN.tex
        P2_Common_Physical_Problem.md
        P2_Reference_Controller.md
        P2_Optimization_Controller.md
        P2_RL_Controller.md
        P2_Implementation_Mapping.md
    references/
        README.md
        bibliography.bib
        P1/
            P1_reference_audit.md
            P1_optimization_audit.md
            P1_rl_audit.md
        P2/
            P2_reference_audit.md
            P2_optimization_audit.md
            P2_rl_audit.md
```

## Required freeze documents

The final problem-level science contracts are:

```text
P1_volt_var_der/P1_VoltVAR_DER_ControlScience_FROZEN.tex
P2_restoration/P2_Reconfiguration_Restoration_ControlScience_FROZEN.tex
```

The C0A versions of these files are placeholders only.

## Architecture references

Also preserve the simulator/controller development philosophy in the architecture
documentation, including:

`docs/development/architecture/OpenDSSSim_Parallel_Simulator_Controller_Development_Philosophy_v01_20261005.md`

when that document is present in the repository.
