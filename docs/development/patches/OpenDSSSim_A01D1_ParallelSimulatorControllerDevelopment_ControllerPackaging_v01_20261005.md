# OpenDSSSim_A01D1_ParallelSimulatorControllerDevelopment_ControllerPackaging_v01_20261005

## 1. Patch identity

- Patch ID: `OpenDSSSim_A01D1_ParallelSimulatorControllerDevelopment_ControllerPackaging_v01_20261005`
- Date: 2026-10-05
- Stage: A01D1
- Type: **documentation-only architecture checkpoint**

## 2. Objective

Permanently record the parallel simulator/controller development philosophy and the intended generalized-controller repository organization before A02 begins.

This patch does not implement controllers or modify simulator behavior.

## 3. Predecessor

Authoritative predecessor:

`OpenDSSSim_A01_AltDSS_Foundation_Context_Snapshot_v01R1_20261005`

A01 qualified source-manifest SHA256:

`3396BC748F3EF763934A4434A02160E81FB3E2B68C10B0C05E137105422C6CD4`

A01 status:

- installer PASS;
- standalone validator PASS;
- independent validator PASS;
- pytest 14/14 PASS;
- predecessor identity preserved.

## 4. Directed input

Input bundle:

`OpenDSSSim_A01D1_ParallelDevelopment_DirectedInput_v01_20261005_185526.zip`

Input bundle SHA256:

`3069DC845549438EAD648E5454855253F136DFD261DD2BBF52CD4C6BD5F7A7E6`

Environment:

`scalebridge-dev-gpu-laptop`

The fresh POST-A01 source manifest matched the frozen A01 qualified source manifest exactly.

## 5. Frozen architectural decisions

A01D1 freezes:

1. explicit parallel simulator and controller-science tracks;
2. simulator ownership of AltDSS and all physical plant transitions;
3. prohibition on controller AltDSS imports/manipulation;
4. `env.step(...)` as the authoritative Gymnasium mutation boundary;
5. requested/applied/realized action ownership by the simulator;
6. controller capability-requirement semantics;
7. the definition of circuit-general controller compatibility;
8. intended controller package organization;
9. control-science documentation organization;
10. A02/A03/A04/A05 synchronization points;
11. no hard-coded IEEE-123 object names in generalized controller source;
12. no premature controller implementation before science/interface freeze;
13. explicit information/fairness contracts for paper comparisons;
14. no controller-algorithm novelty claim for the six paper controllers.

## 6. Files added

Exactly three repository files are added:

```text
docs/development/architecture/
    OpenDSSSim_Parallel_Simulator_Controller_Development_Philosophy_v01_20261005.md

docs/development/control_science/
    README.md

docs/development/patches/
    OpenDSSSim_A01D1_ParallelSimulatorControllerDevelopment_ControllerPackaging_v01_20261005.md
```

## 7. Files forbidden from modification

A01D1 must preserve every one of the 32 predecessor files byte-for-byte, including:

- all Python source;
- all tests;
- the A01 DSS fixture;
- `pyproject.toml`;
- root `README.md`;
- A0 architecture documents;
- A01 permanent patch record.

## 8. Environment policy

Environment mutation: **NONE**.

No package installation is permitted.

`gurobipy` remains deferred.

## 9. Qualification contract

Installer and independent validator must prove:

- active environment is `scalebridge-dev-gpu-laptop`;
- patch ZIP SHA256 matches its frozen value;
- all 32 predecessor files match bytes and SHA256 from the directed-input manifest;
- patch payload hashes match;
- only the three permitted new documentation files are installed;
- all 32 predecessor files remain unchanged after installation;
- no unexpected non-cache repository files exist;
- A01 standalone behavior remains PASS;
- A01 pytest regression remains PASS;
- environment fingerprint is unchanged across installation.

## 10. Rollback

Because A01D1 is additive and documentation-only, rollback removes only the three files added by this patch and prunes `docs/development/control_science/` if empty.

No predecessor file may be modified during rollback.

## 11. Controller source status

No `src/opendsssim/controllers/` source tree is created by A01D1.

Its intended organization is documented, but implementation waits for:

- literature-backed P1/P2 science freeze; and
- the required simulator-side contracts.

## 12. Successor

Plant/simulator development proceeds immediately to:

**A02 — generalized engine and circuit capability discovery.**

The controller-science track continues in parallel and synchronizes through the contracts defined in the architecture document.
