# A05.1 - Clock, Episode, and Snapshot-Timing Semantics

**Ratified:** 2026-10-26  
**Status:** DESIGN RATIFIED; NOT IMPLEMENTED; NOT QUALIFIED  
**Predecessor:** A04I4A v02, 195 qualified source files  
**Predecessor source-manifest SHA256:** `5E2C6DE82802533C283EB884987B999345D9BAFBFD6C09A439949B8C15A47045`

## 1. Scope and preservation

A05.1 adds a simulation clock and episode lifecycle to the existing A04 Gymnasium/AltDSS plant. It does not revise the frozen `Plant != Problem != Controller` architecture, semantic registries, strict Gym Dict contract, immutable A04 runtime binding, preflight identity, requested/applied/realized action audit, static-fault precedence, or H0-H3 history retention policy. The separate FAST/STANDARD/AUDIT execution-profile axis remains orthogonal.

The A04 snapshot runtime exists, but a bound timestamp, external profile writer, episode horizon, post-terminal guard, and consistent temporal metadata are **not yet implemented**. This document authorizes no source implementation and makes no claim that A05 runtime behavior has passed tests.

## 2. One authoritative external clock

An A05 episode has a start timestamp `t0`, positive fixed duration `dt`, and completed-control-step counter `n`. For intervals with index `k`:

`t[k] = t0 + k * dt` and `interval[k] = [t[k], t[k+1])`.

- All canonical timestamps are timezone-aware UTC. Source-local timestamps require an explicit, unambiguous conversion, with DST/duplicate/missing-time policy qualified in A05.3.
- The default `t0` is the **first jointly valid timestamp** across all required bound exogenous signals, rather than independently choosing different beginnings per file.
- An explicit valid user reset selection may override the start within available coverage.
- With no timestamped exogenous series, use a deterministic generic UTC origin (`2000-01-01T00:00:00Z`). The numerical generic `dt` default, if not provided, is an A05.3 detail; no installed A05.1 implementation may silently assume a data resolution.
- A user-configured episode step limit `N` may be independent of source-series length. `strict` versus `tile` replay and forecast indexing are separately ratified in A05.3/A05.4.
- OpenDSSSim, not OpenDSS, advances the authoritative clock. No native `Daily`, `Yearly`, or `Duty` time-series loop is used.

## 3. `reset()` contract

`reset(seed=..., options=...)` has a simple default and an optional validated reset-selection function. The reset-selection function may select start/episode parameters; it may not replace the plant's actual restoration or bypass frozen authority.

1. Validate the episode specification, source/profile identity, required coverage, selected start, and seed.
2. Restore/recompile the baseline in the environment-owned AltDSS context as permitted by A04; verify binding/preflight identity.
3. Apply A04 native/external/hybrid authority, competing-native-control suppression, and static fault `Enabled=False` state.
4. Establish `t0`, select and apply exogenous truth sample `d[0]`, and apply initially scheduled events in their later-ratified A05.7 order.
5. Execute **one authoritative initial Snapshot solve** with the qualified native STATIC control configuration.
6. Read the initial observation, solution, state and provenance; append a `phase=reset`, `completed_steps=0` history record.
7. Return `(observation, info)` without manufacturing a reset reward, termination, or truncation result.

A failed reset raises an explicit exception. A new reset clears the prior episode history and state, and does not create a new AltDSS context merely to change episodes.

## 4. `step()` contract - ratified Option A

For the current decision interval `k = n`, `step(action[k])` applies that interval's exogenous sample `d[k]`, evaluates the authorized action, performs the snapshot solve, records the outcome, and **only then** advances the logical decision clock to `t[k+1]`.

Canonical pipeline:

1. Reject calls before reset, after episode completion, after a failed/inactive episode, or when a configured horizon is already exhausted.
2. Validate the exact A04 Gym Dict action and finite values.
3. Select deterministic `d[k]`, apply its registered load/PV/weather properties, then scheduled exogenous events; uphold static fault precedence and A04 native control authority.
4. Apply A04-admissible external action commands without silent clipping, projection, feasibility fallback, or co-control.
5. Execute **one authoritative** `solve_snapshot()` invocation in the same live context; native STATIC controls may perform their own internal control/power-flow iterations.
6. Read convergence, realized actuator state, observation, required internal state and other configured signals; evaluate reward/termination/truncation functions.
7. On success, atomically commit the transition and its history record, increment completed steps, and advance the external decision clock to `t[k+1]`.

The reset solve and `step(action[0])` both use sample `d[0]`: reset establishes the pre-action operating point, while the step establishes the controlled interval-0 operating point. Any stochastic perturbation for that sample is **the same realization**, not a second random draw.

**Do not conflate timestamps:** After the first successful step, `completed_steps=1` and the next decision begins at `t[1]`, but the latest electrical solve used the input sample at `t[0]`. A returned observation must be labelled with its actual electrical-sample timestamp; it is not falsely described as an additional `t[1]` power-flow solve. This is intentional under current-interval Option A.

For `N` successful controller steps, an ordinary complete episode performs one initial solve plus `N` authoritative step solves. `N` samples (`d[0]` through `d[N-1]`) suffice under strict current-interval indexing, excluding any separately declared forecast requirements.

## 5. Snapshot solver and native STATIC controls

- `Solution.Mode = Snapshot` and `Solution.ControlMode = STATIC` are the required A05 run semantics.
- STATIC is an OpenDSS **solution-level control mode**, not an independently selected mode for each individual controller.
- Native regulators, capacitor controllers, and other native controllers act only when enabled, qualified, and retained by the frozen A04 NATIVE/HYBRID authority partition.
- A capacitor switching decision follows its own `CapControl` type, monitored point/phase, thresholds, hysteresis/delays and enablement. There is no invented universal `V < 0.95 pu` trigger.
- STATIC performs queued control processing during a snapshot without modelling wall-clock control delays across real episode intervals. Multiple internal iterations do not constitute multiple authoritative OpenDSSSim steps.
- External time is authoritative. The exact safe mapping to AltDSS Solution `Year/Hour/Seconds` and any repeated Snapshot-mode setter side effects **remain directed A05 qualification items**, not an untested implementation assumption. Never silently select EVENT/TIME mode.

## 6. Default and custom reset/reward/termination/truncation

| Function | Default | Optional user choice |
| --- | --- | --- |
| reset selection | first jointly valid exogenous timestamp; generic deterministic UTC otherwise | validated alternative start/options selector |
| reward | finite scalar `0.0` | custom finite-scalar reward |
| termination | `False` | custom boolean termination |
| truncation | `True` at configured finite horizon or end of valid strict-mode data; otherwise `False` | custom boolean truncation, still subject to hard data/episode safety boundaries |

Defaults are neutral and available without a user hook. An absent custom function must not be replaced with a fabricated heuristic. A custom stop function may terminate or truncate earlier; it cannot authorize out-of-range profile reads or bypass mandatory control/authority checks. If a physical termination and time boundary occur simultaneously, both truthful flags/reasons are preserved.

Preserve existing A04 custom hook callables receiving immutable `RuntimeStepContext`. A05 may add an **opt-in** callback interface that receives comprehensive **read-only** access to simulator data (state, history, clock, solution, controls, exogenous truth and qualified semantic readouts), plus the current context. Do **not** pass a mutable backend/environment `self`: hooks cannot write plant states, bypass authority, issue actions, reset, or cause extra authoritative solves. A reset selector similarly chooses parameters without replacing reset mechanics. Existing A04 hooks and their provenance hashes remain backward-compatible.

## 7. Provenance, history and controller visibility

Temporal metadata for each reset/step includes, as applicable: `episode_id`, decision index, completed-step count, `t0`, `dt`, electrical sample timestamp, half-open interval start/end, next decision timestamp, exogenous sample/source identities, replay/noise seed identity, and qualified engine-time status.

- The minimum time identity is retained even at history H0; H1-H3 retain their existing contracted data and may additionally carry temporal details. FAST/STANDARD/AUDIT must not change physical or clock semantics.
- Temporal provenance participates in run/evidence manifests; A04 preflight remains valid only for its frozen identity, and new A05 identities must not falsely reuse an A04-only qualification as A05 qualification.
- Plant truth and audit `info` do **not** automatically enter the Gym observation. Controller-visible time, disturbance, forecast and hidden truth are selected through the later A05.6 information contract.

## 8. Episode completion and failures

- After a successful step returning `terminated=True` or `truncated=True`, subsequent `step()` raises until an explicit new `reset()`.
- A structured `converged=False` is a valid recorded electrical outcome and is passed to configured hooks; it is not silently converted to invalid action status.
- Backend exceptions, missing mandatory data, invalid required reads or hook exceptions cause explicit failure, with **no successful history record or committed clock advance**. Because the backend may already be partly mutated, the episode becomes inactive until reset.
- No rollback of physical electrical writes is falsely claimed after a mid-step exception; explicit reset is the recovery boundary.
- The simulator does not hide failed steps by repeating the prior observation, filling NaNs, or inventing a substitute action.

## 9. Ratified versus deferred details

**Ratified A05.1:** external UTC clock, first-common-sample reset, Option A interval solves, Snapshot/STATIC, default/custom function model with read-only simulator view, explicit finite episode termination/truncation behavior, time metadata, failure lockout and frozen A04 authority.

**Deferred by design:** channel/device binding and units (A05.2); profile coverage/resampling, concrete generic `dt` default and `strict`/`tile` rules (A05.3); forecasts (A05.4); uncertainty implementation/seed derivation (A05.5); controller information disclosure (A05.6); dynamic fault/event ordering and full qualification (A05.7). Detailed AltDSS engine-clock mirroring, native STATIC switching behavior and Solution.Mode setter effects require directed tests before implementation freeze.

## 10. Required future qualification

1. First-common-timestamp selection, UTC conversion, deterministic generic origin, valid reset overrides.
2. Reset versus first-step sharing of `d[0]`, including stochastic realization identity.
3. `N` steps yielding exactly `N+1` authoritative solves and no off-by-one input accesses.
4. Truthful electrical-sample versus next-decision timestamps in `info` and H0-H3.
5. Native STATIC capacitor/regulator execution in a genuine AltDSS fixture, with EXTERNAL suppression and HYBRID partition checks.
6. Solution.Mode/engine-time setter side effects and unchanged A04 no-profile behavior.
7. Default hooks, opt-in read-only custom hooks, stop precedence, post-terminal lockout, invalid action and hook/backend failure recovery.
8. A04I4A successor regressions, provenance/preflight compatibility and complete source/evidence freeze.

**Final design disposition:** A05.1 RATIFIED. Documentation-only installation is permitted; A05 runtime/source implementation awaits the applicable A05 implementation plan and qualification authority.
