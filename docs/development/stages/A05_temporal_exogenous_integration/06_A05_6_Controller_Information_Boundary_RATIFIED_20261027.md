# A05.6 — Controller Information Boundary, Health, and Forecast Visibility

**Ratified:** 2026-10-27 (America/Los_Angeles)  
**Status:** DESIGN RATIFIED; DOCUMENTATION ONLY; A05 RUNTIME NOT IMPLEMENTED OR QUALIFIED  
**Predecessor:** A05.5 docs-only, 205 files (laptop PASS reported by user)  
**Predecessor manifest:** `OpenDSSSim_A05_5_DocsOnly_Qualified_SourceManifest_20261028T003509205Z.csv`  
**SHA256:** `50EA36EA13A4E07BBF7B78B88AD71453DE60A51551D8C0F4E1D52EA9A6D2DB7E`

## 6.1 Four information categories; current device health

1. **Physical truth**: actual current physical state/exogenous sample, complete future source profiles, present and future faults/events, internal AltDSS states and protected provenance. Not automatically public to a controller.
2. **Measured/permitted current observation**: only fields explicitly resolved by the A04 ProblemSpec and its typed Gym space, including device status when authorized.
3. **Controller forecast**: optional A05.4/5 qualified one-trajectory future exogenous representation, obtained by request or via a declared observation field.
4. **Trusted diagnostic view**: H0–H3 records and full physical-source/solver audit through explicit protected, read-only diagnostic access, separate from ordinary Gym data.

**User amendment:** the controller is entitled to the available **current** device health, enabledness, operational availability and effective commandability when those fields are discoverable and relevant. Expose status generically by registered device identity, phase and permitted semantic capability. Distinguish physical connected/present, enabled/disabled, healthy/faulted, controllable/not-controllable and unknown/unobserved; never silently infer `healthy` from missing health data or invent sensors. Device health here is present information, **not** lookahead to future event schedules. Fields enter Gym only when declared in the ProblemSpec/space, otherwise may enter typed read-only context if permitted.

## 6.2 A05.1 Option-A timestamps retained

At `reset()`, apply qualified `d[0]` and perform the initial snapshot solve at `t[0]`. At `step(action[0])`, execute the interval using the same physical `d[0]`, perform its snapshot solve, then advance the **logical decision boundary** to `t[1]`; the latest **electrical sample** remains timestamped `t[0]`. Subsequent steps follow the same contract. Expose and never conflate `decision_time`, `electrical_sample_time`, `completed_steps` and physical interval where relevant. The next forecast is issued at the logical decision time; generating/reading forecast, status or observation adds **zero AltDSS solves**. Preserve reset, termination and truncation alignment without fabricated samples.

## 6.3 ProblemSpec-controlled Gym observations and H0–H3 recording

The frozen A04 resolved nested Gymnasium `Dict` is authoritative. P1 may contain permitted bus/phase voltages, device P/Q measurements and regulator/capacitor/PV operational states; P2 may contain qualified switch/topology status. These are possible A04 mappings, **not** a mandate to expose everything. New health/status or forecast observation fields need an explicitly valid ProblemSpec/schema declaration and dimension/unit checks, not a silent runtime extension to A04's frozen space. Arbitrary AltDSS variables, future-truth tables, custom graph embeddings or solver internals remain out of the default observation. Feature scaling, graph construction and estimation belong to the controller.

**User amendment:** preserve existing recording hierarchy H0/H1/H2/H3 and FAST/STANDARD/AUDIT execution profiles. No new parallel logging tier. Level choices may change diagnostic richness and execution overhead, but must **not** change plant truth, snapshots, device authority, forecasts, physical actions or clocks. Storage and access for rich audit are trusted/independent, not automatically controller-visible in `info` or Gym. Existing authoritative H0–H3 field definitions remain in force; this subsection does not reassign their specific fields.

## 6.4 Forecasts optionally included in observations

The only future exogenous provider is A05.4 derived from the same user-defined physical exogenous sources, transformed by A05.5 mode `none` or `additive_gaussian`. It produces one seeded trajectory per issue time, not a scenario ensemble. A controller may access a read-only forecast service; **alternatively the resolved ProblemSpec may explicitly place forecast values in its Gym observation**. In that case shape, units, channels/entities, issue timestamp, target timestamps, lead indices, horizon, allowed uncertainty metadata and unavailable/missing policies must be part of the resolved observation contract. Never append an undeclared forecast tensor to a frozen Gym Dict. Reading via the two authorized routes must yield the **same** seeded realization for the same record, without new solve or resample.

The public result may contain the forecast, declared sigma/noise mode and validity metadata, not separately the protected unperturbed future source, raw random draws or mutable forecast cache. For scientific reporting, `none` and zero sigma are **oracle/perfect exogenous foresight** diagnostics, and positive Gaussian error is a **synthetic future-truth-based benchmark**, not a causal forecasting model. Making that explicitly contracted forecast part of observation is permitted and does not constitute leakage beyond the agreed policy.

## 6.5 Read-only controller context and network/device information

Provide a typed, read-only `ControllerContext` (precise API naming deferred to implementation), scoped to authorized fields:

- permitted current observation and electrical sample timestamp;
- logical decision clock, step/index and episode identity;
- declared/queried single-trajectory forecast or typed absent/unavailable result;
- public static circuit/device metadata and ratings, permitted **current** connectivity, bus/phase mappings, current operational device statuses, health and active controllability;
- permitted control/action-space semantics, bounds, masks and prior **realized** actuation feedback;
- supported optional capability and source-bus/topology descriptions needed to construct a controller-side decision model.

**No mutable AltDSS context, backend implementation reference, unrestricted truth cache or controller-specific solution** is handed out. The controller decides slack/source-bus abstraction, forecasting needs, PV curtailment strategy, graph representation, LinDistFlow approximation, and policy logic; the simulator reports qualified information and enforces physical authority. P1 and P2 may expose different typed subsets. Unknown, unavailable, unsupported and disabled are explicit states rather than silent coercions.

## 6.6 Equal entitlements, controller-chosen forecast requirements

Within a fixed P1 experiment, RBC/MPC/RL have the same *eligible* authorized measurements, device capabilities, possible forecast channels and physical plant/action authority under a shared ProblemSpec and exogenous/seed policy; apply independently to P2. **User amendment:** each controller decides whether it needs forecasts, which qualified channels, how many leads, and whether a missing forecast is required/fatal or optional. It may use none, a subset, or a shorter horizon. The simulator must validate a request against available channels, horizon, source coverage, permissions and units, returning typed absence or failure rather than fabricating data. Availability of the same interface does **not** require consumption of the same fields.

For matched `(episode, source, channel, entity, decision-issue, lead, seed)` requests, realizations are controller-independent and repeat-call stable. Common-source/controller comparison remains scientifically fair with **equal entitlement**; reports must disclose materially different information actually requested/consumed. A deliberately asymmetric information policy must be labeled accordingly, not called equal-information comparison.

## 6.7 Practical division of responsibilities, not general-purpose sandboxing

**User amendment:** adopt proportionate boundary protections. The simulator owns correctness of **its official exposed data**: typed/current/physical fields, public `observation` and `info`, declared forecast endpoints, device health, clock and control capability; it must withhold internal mutable AltDSS handles and protected future truth from these default routes. Trusted full diagnostics require an explicit read-only route, never accidental embedding in controller-facing records. Official wrappers and adapters (including SB3-compatible RL integration) should follow that same declared boundary.

The **controller owns** selecting and validating requested channels, health, times, units, required/optional forecast availability, appropriate models and action decisions. It must not reach into private simulator caches, internal debug objects or trusted audit files. The simulator need not recursively police arbitrary user-supplied Python callbacks, third-party extensions, offline data files or deliberately privileged external code. There is no expensive general-purpose security sandbox requirement in V1. **Fail closed on violations of declared official interfaces**, but leave responsible use of legitimately exposed fields to controllers. Any trusted bypass for engineering must be explicitly separated from normal scientific controller execution.

## 6.8 Runtime acceptance tests and no-change boundary

Implementation qualification must demonstrate:

1. Exact A04 Gym Dict shape/dtype/semantic compatibility; newly declared health/forecast observation fields only through resolved space contracts.
2. Reset/step decision vs sample timestamp correctness, with forecast/context/status reads adding no solves.
3. Current enabled, healthy/faulted, unavailable and **unknown** device states; no fabricated sensor or future-event leakage.
4. Read-only `ControllerContext` for permitted current topology and devices; no mutable backend or full future truth.
5. Forecast service/declared-observation parity and repeated-request seeded stability; no extra forecast providers or scenario axis.
6. P1 and P2 RBC/MPC/RL permitted-information parity with controller-specific forecast requirements and typed coverage failures.
7. Standard `observation`, `info`, wrappers and history/audit access separation, maintaining H0–H3 and FAST/STANDARD/AUDIT snapshot invariance.
8. Independently checked predecessor SHA/file count, successor manifest, A03/A04 and A05.1–A05.5 regression behavior, evidence and receipts.

**Disposition:** A05.6.1–A05.6.8 DESIGN RATIFIED with user refinements. This docs-only package does not modify executable code, current feeder/data, environment or physical runtime. **Only A05.7 design ratification remains before the proposed A05 implementation gate.**
