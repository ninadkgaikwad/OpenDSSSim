# A05.7 - V1 Static Device Health, Failure Semantics, and Implementation Qualification Gate

**Ratified:** 2026-10-27 (America/Los_Angeles)  
**Status:** FINAL A05 DESIGN BLOCK RATIFIED; DOCUMENTATION ONLY; A05 RUNTIME NOT IMPLEMENTED OR QUALIFIED  
**Frozen predecessor:** A05.6 docs-only, 207 files, laptop PASS reported by user  
**Predecessor manifest:** `OpenDSSSim_A05_6_DocsOnly_Qualified_SourceManifest_20261028T014829139Z.csv`  
**Predecessor SHA256:** `B7A4207EDC14A3D3B53C3E326B70D7BD6EA18215DED26EB35546C5DC27E0FE47`

## 7.1 No dynamic physical-event generator in V1

**User amendment supersedes preliminary 7.1:** V1 requires NO time-varying exogenous equipment faults, repairs, outages, health changes or dynamic availability schedules. The qualified **ProblemSpec at initialization** determines whether a device is healthy/available/enabled and hence commandable. Existing A03/A04 static fault and initialization semantics remain authoritative; A05 must not invent a second event mechanism. Unhealthy/disabled devices are represented by the resolved initial physical/operational state and remain so for the episode, unless an already-frozen native mechanism specifically governs a permitted state transition; A05 adds no exogenous toggling functionality. A controller may observe permitted current health/enabledness through A05.6, including explicit unknown state if no status is available.

## 7.2 Exogenous inputs remain time-varying physical trajectories, not events

**User amendment supersedes preliminary 7.2 event sequence:** A05's time-dependent exogenous inputs are qualified **load active/reactive power or signed-PF representation, PV irradiance and weather variables, and other explicitly declared continuously sampled physical disturbance channels** from A05.2–A05.3. CSV/Parquet or other user-defined exogenous source remains the physical truth authority. Exogenous inputs do **not** carry device-enable/disable, switch open/close, outage/repair, or topology-change events in V1.

At reset: resolve the ProblemSpec's fixed initial health/enabledness/authority, apply the initial exogenous sample and perform the approved initial snapshot solve. For a step: resolve physical exogenous data; validate and admit the **controller** action subject to static device state and A04 authority; execute exactly the approved snapshot power-flow solve; read/audit and advance A05.1's Option-A clock. The reset/step relation for `d[0]` remains unchanged. Forecast/context reads are non-mutating and cause no solve.

## 7.3 Event replay/reset machinery is out of V1 scope

**User amendment supersedes preliminary 7.3:** No latched fault events, repair transitions, periodic event replay, event-cycle restoration or event-specific reset state machine shall be implemented. A05.3's strict/tile replay is **only** for qualified physical time-series inputs. Episode reset restores the A04/A05.1 qualified initialization and static ProblemSpec device conditions, not a new dynamic event history. No implicit extra topology changes are allowed through exogenous records.

## 7.4 Preserve requested/applied/realized actuation; no exogenous switching

Retain separate per-device/per-phase action records, when meaningful:

`u_requested[t]` = controller's submitted action;  
`u_applied[t]` = admissible command delivered to the physical backend under A04 action/authority/initial availability;  
`u_realized[t]` = actual post-solve device or electrical state/readout, when measurable.

These may differ because of range checks, A04 authority, device initialization, native control behavior or solver outcomes; **never label an unapplied request as realized**. Preserve A04 native/EXTERNAL/HYBRID authority and conflict-precedence rules. No user-defined exogenous source may toggle switch position, topology or enabledness in V1. **P2 controller-requested switching/reconfiguration remains explicitly in scope**, using the frozen P2 action resolution and Plant actuator binding. Thus controller actions *may* change present topology through an authorized switch command; there is simply no independent exogenous topology-event provider.

## 7.5 Do not add exhaustive deterministic/cache-replay qualification

**User amendment:** do **not** create a new A05.7 test matrix comparing fresh/reused caches, independent environments, repeated whole-episode numerical trajectories or various runtime cache modes. Preserve the previously ratified seed-keyed determinism for A05.5 forecast calls, A05.1 episode semantics and A04 environment-context isolation as design requirements, but **no dedicated broad replay/cache parity campaign is authorized in V1**. Avoid overstating that an unperformed experiment has passed. Narrow, local smoke checks needed for correctness of newly added code are allowed under A05I1–I6; these do not imply the declined exhaustive campaign.

## 7.6 No new H0–H3 or FAST/STANDARD/AUDIT physical-parity sweep

**User amendment:** the existing design requires recording and execution profiles to be **semantically noninvasive** (H0–H3 and FAST/STANDARD/AUDIT must not intentionally change plant physics, actions, time or forecasts). This is retained as a **design invariant**, but A05 V1 does **not** add a complete cross-product qualification suite to numerically compare all profiles and history levels. Preserve their existing interfaces and already qualified A04 tests. Do not claim that an all-profile physical equivalence sweep was executed. Directed tests of actual A05 changes may still run under a representative profile.

## 7.7 Typed failures, explicit status and no disguised success

Agree to typed, attributable outcomes for malformed/missing required time-series inputs, invalid source/entity/channel mappings, wrong units/shape, unavailable required forecast, action authority conflicts, actions targeting initially disabled/unhealthy devices when disallowed, invalid controller switch actions and nonconvergent AltDSS snapshot solves. Retain requested/applied/realized command evidence and failure reason. A physically unsafe/invalid partial step must not be returned as successful: mark the step or episode failed/terminated/truncated using the existing Gym/A04 contract, recording any known partial execution and requiring a safe reset when continuation cannot be guaranteed. Do not invent a hidden fallback controller action, silently change topology, repair a device, fabricate measurements or automatically add extra solver iterations outside the approved snapshot policy.

## 7.8 Implement in a NEW CHAT through evidence-first gated development

The final A05 design contract consists of A05.1–A05.7 and their installed docs. This patch concludes design ratification only; do not equate docs-only PASS with implemented temporal/exogenous runtime. After A05.7 installation/qualification, initiate implementation in a **new conversation** and adhere to this order:

1. **Read-only repository tree and baseline inventory.** Collect an evidence ZIP into the user's Windows **Downloads**, including a qualified source-manifest check, directory/source/test tree and IEEE-123 feeder candidate paths; upload to the new chat. No guessed paths or implementation edits.
2. **Directed evidence request.** Inspect the tree, select *actual* relevant source/tests/feeder/config files, and supply a new read-only directed source collector (including bounded evidence and SHA checks). User runs it from repo root, resulting ZIP in Downloads, then uploads it. Only now read exact source contracts and resolve the patch design.
3. **Implement small guarded stages** using exact pinned predecessor manifests/hashes, full unit/contract tests and real feeder validation where applicable. Provide ZIP installer, validator, optional recoverable rollback and generated evidence under Downloads. Do not overwrite frozen predecessors without a specific reviewed patch.

Proposed implementation gates (names are **now accepted as the execution roadmap**, but detailed patch interfaces are not preapproved):

| Gate | Scope and local evidence |
|---|---|
| A05I1 | A05.1 episode clock, reset, stepping and timestamp fields; targeted Gym/clock qualification. |
| A05I2 | A05.2 typed user-supplied P/Q/PF, PV and weather binding, static ProblemSpec device status, snapshot AltDSS application; real feeder checks. |
| A05I3 | A05.3 source indexing, CSV/Parquet, strict/tile, arbitrary duration, provenance; selected edge cases. |
| A05I4 | A05.4/A05.6 one-source future forecast, optional observation field, typed read-only controller context; targeted nonleak/zero-solve tests. |
| A05I5 | A05.5 exactly one seeded `none` or additive-Gaussian **forecast-only** error trajectory, physical-domain handling and provenance. **No dynamic-event subsystem.** |
| A05I6 | Whole A05 bounded qualification: integration/regression and direct AltDSS checks using the real canonical IEEE-123 and shared working feeder; source/environment/evidence freeze. **No declined exhaustive matrices from 7.5/7.6.** |

The real IEEE-123 baseline must be discovered from actual repository-tree evidence (no invented circuit paths). Keep original/native 7 regulator controls and 4 capacitors and the identified switch-like lines intact. For P1, preserve the **exactly 10 PV additions** of the `ieee123_pesgm2027` working feeder; do not add artificial regulators/capacitors. Use baseline feeder as a physics/semantic reference and working feeder for P1/P2 end-to-end tests. Validate against direct AltDSS, including snapshot counts, convergence, initialized device availability, P1 exogenous loads/PV, P2 controller switch controls, A04 authority/registries/Gym and expected physical readouts. No full scientific RBC/MPC/RL six-scenario campaign until the implementation gate explicitly authorizes it.

Every delivered gate should provide: full file manifest and SHA256, explicit source changed/unchanged list, environment/dependency record, test command and results, real-feeder comparison evidence when relevant, and a read-only evidence ZIP in Downloads for independent upload. Never build a runtime patch from memory or invented repository paths.

**Final disposition:** A05.7.1–A05.7.8 DESIGN RATIFIED with user-requested V1 exclusions. **A05.1–A05.7 design ratification complete, pending this A05.7 documentation-only installation and successor qualification.** Start implementation in a new chat from tree → directed bundle → source-grounded patch → bounded tests → qualified evidence. No A05 runtime implementation or scientific controller experiments are claimed by this patch.
