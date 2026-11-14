# OpenDSSSim A05I1A — Runtime Reliability Concern Register (V01)

**Recorded:** 2026-10-28 Pacific / 2026-10-29 UTC  
**Scope:** A05I1A episode clock, A02/A03/A04 AltDSS dependencies  
**Status:** A05I1A **functionally qualified under its defined acceptance contract**; two reliability concerns are **OPEN**. This record is not a bug-fix claim or V1 release sign-off.

## 1. Qualified engineering baseline

- Patch: `OpenDSSSim_A05I1A_ExternalEpisodeClock_v01_20261028`.
- Qualified 212-file source manifest SHA-256: `1BA0341C27595917BFD4A38DDE02CF41E22E28A6FA3A3907A358A9671A4AC578`.
- Three consecutive independent runs each passed **16/16 targeted tests** (including real canonical IEEE-123 and P1 working-feeder AltDSS checks) and **108/108 full-repository tests**. All three checked unchanged predecessor hashes before and after tests; validator returned `PASS_A05I1A_INDEPENDENT_QUALIFICATION` with exit code zero.
- Environment in receipts: `scalebridge-dev-gpu-laptop`, Windows, Python 3.10.20, AltDSS 0.2.4, pytest 9.1.1, Gymnasium 1.2.3.

Qualification evidence (Windows Downloads):

| Evidence ZIP | SHA-256 |
|---|---|
| `OpenDSSSim_A05I1A_QualificationEvidence_20261029T003533716194Z.zip` | `E85FB0122EA572673D7F889E31CE24E122A37D61F4E6D7E3158C309885102037` |
| `OpenDSSSim_A05I1A_QualificationEvidence_20261029T003603666809Z.zip` | `49F0EF183B3ABBA900189333B47749FBC3365CB0688A94335F598223D326D246` |
| `OpenDSSSim_A05I1A_QualificationEvidence_20261029T003636214653Z.zip` | `39F025C7350CC0F9E6F07571004E4445C5CBFC80C19CD975ECF6B7FBA1BBE1F2` |

## 2. Open concerns

### R01 — Native Windows exception traces on AltDSS/DSS-Python import

Every passing qualification run printed eight `Windows fatal exception: code 0xe0465043` traces to targeted stderr and eight to full-regression stderr. Stacks enter `dss_python_backend` during AltDSS import and pytest collection; pytest continued and passed. We **do not know** whether these are handled native exceptions, dependency initialization behavior or a deeper defect. Do not suppress stderr or declare them harmless based only on exit status.

**Next diagnosis:** Compare fresh-process `dss_python_backend` and `altdss` imports *without* OpenDSSSim; record exit codes, exception trace, installed versions and native DLL identity. No dependency change without an independent authorization/qualification step.

### R02 — Intermittent malformed native JSON for synthetic capacitor

An earlier combined integration sequence failed at frozen `src/opendsssim/backends/altdss_backend.py`, `json.loads(obj.to_json(_DISCOVERY_JSON_FLAGS))`, discovering `Capacitor.cap1` in **synthetic** `tests/fixtures/a03_semantic/Master.dss`. The failure occurred in `test_a04i4_multiple_steps_resets_authority_and_history[HYBRID]` near JSON character 348 or 372 (20 tests passed, next failed). Isolated A04I4 passed 4/4; separate predecessor groups passed 16/16 and 11/11; subsequent combined tests passed 23/23 and full qualifications 108/108 × 3. A read-only `json.loads` interception probe did not reproduce the failure.

**Unknown:** Exact invalid JSON token, source of order sensitivity, and whether native serialization, context state or discovery behavior caused it. The A05I1A clock patch was **not proven** causal.

**Next diagnosis:** If it recurs, capture the *entire* unmodified native JSON string and exact failing offset with class/name, context, test order and versions. Compare fresh independent AltDSS contexts. Do not silently sanitize invalid numbers, skip devices or edit frozen A03/A04 code without a separately authorized evidence-backed fix.

## 3. Change control and V1 gate

1. **A05I1A engineering qualification PASS** does **not** close R01/R02 or prove crash-free operation.
2. Continue small A05 stages with exact successor-manifest identity, complete A03/A04 regression, and direct AltDSS checks on the **base IEEE-123** and the approved **P1 working feeder**. Add P2 physical tests when a patch touches P2 behavior.
3. This documentation patch changes **one Markdown file only**; no A01–A04 source, runtime code, feeder files, controller code, package versions or environment settings are modified.
4. No dynamic exogenous faults/repairs/switching events are introduced. A04 controller-requested switching stays authorized. No unqualified AltDSS Year/Hour/Seconds clock forcing is permitted.
5. Before **final OpenDSSSim V1 release qualification**, each concern needs a demonstrated root cause and verified fix **or** an explicit bounded evidence-based non-blocking disposition, reviewed independently. Three green regressions alone do not satisfy this closure criterion.

## 4. Closure template

Append a separately versioned record for each issue: reproduction/environment, raw evidence with SHA-256, root cause or justified limitation, correctness/availability impact, correction or containment, negative and real IEEE-123 regression tests, and signed-off disposition. Preserve this historical V01 record.
