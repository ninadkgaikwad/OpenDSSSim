# Controller-Science Architecture

**Status:** C0A scaffold / architecture bridge

## 1. Architectural reconciliation

The A0 baseline distinguishes reusable simulator source from paper-specific validation
workloads. The controller-science handoff further requires generalized controller
implementations that can instantiate on compatible circuits.

These are compatible when separated as follows:

- `src/opendsssim/controllers/` — later reusable, capability-driven controller
  implementations;
- `configs/controllers/` — later reusable controller configuration schemas/defaults;
- `experiments/pesgm2027/` — paper-specific IEEE-123 object selections, feeder
  modifications, scenario parameters, checkpoints, and campaign orchestration.

Therefore, the six PESGM scenarios are still external validation workloads even when
their controller algorithms are implemented through reusable controller classes.

## 2. Non-negotiable interaction boundary

```text
literature / frozen controller science
              |
              v
       ControllerContext
              |
              v
         controller
              |
              v
            a_req
              |
              v
      OpenDSSSim env.step(...)
              |
              v
 validation / admissibility / projection policy
              |
              v
          a_applied
              |
              v
     authoritative plant solve
              |
              v
          a_realized
              |
              v
 observation / metrics / recorder
```

Only OpenDSSSim owns physical plant mutation.

## 3. Controller-consumable services

Future controllers may consume only frozen controller-independent services:

- `ProblemSpec`;
- current observation;
- explicitly authorized state view;
- forecast view;
- capability and registry metadata;
- action schema;
- non-mutating topology/model service exposed by OpenDSSSim;
- episode/time metadata.

A controller may not reach through these services to mutate backend state.

## 4. Current A01 condition

A01 is intentionally below the future controller boundary:
- the observation surface is only convergence;
- the action space is the empty dictionary;
- no generalized state/action registries exist yet;
- there is no controller implementation surface to bind to.

Therefore C0A adds documentation only.

## 5. Synchronization points

- **A02**: controller science supplies capability concepts; simulator owns discovery.
- **A03**: controller science consumes native registries.
- **A04**: `ProblemSpec` + Gym spaces become the main integration boundary.
- **A05**: exogenous disturbance/forecast execution becomes available.

Any missing simulator capability is recorded in
`Simulator_Interface_Requirements.md`; it must not be bypassed inside controller code.
