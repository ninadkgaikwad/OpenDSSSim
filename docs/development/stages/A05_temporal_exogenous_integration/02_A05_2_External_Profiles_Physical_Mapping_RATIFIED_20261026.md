# A05.2 - External Exogenous Profiles and Physical Mapping

**Ratified:** 2026-10-26 (America/Los_Angeles)  
**Status:** DESIGN RATIFIED; DOCUMENTATION PATCH ONLY; RUNTIME NOT IMPLEMENTED / NOT QUALIFIED  
**Predecessor:** qualified A05.1 documentation-only successor, 197 source files  
**Predecessor qualified source-manifest SHA256:** `41E68C88F850130CD6D556AF2B36BF3DB54E5B266216E3E3D4BFA478E6DE837C`

## 1. Scope, ownership, preservation (A05.2.1)

A05.2 defines explicitly sourced physical exogenous profiles and device mappings, independently of OpenDSS native Daily/Yearly/Duty time-series operations. OpenDSSSim selects one dataset sample per Snapshot; the ratified A05.1 Option A `reset()`/`step()` clock is unchanged. Preserve `Plant != Problem != Controller`, A03/A04 semantic/action registries, native/external/hybrid authority, faults, strict Gym Dict actions, no action clipping, and H0-H3 audit.

Conceptually `d[k]=(P_load[k],Q_load[k],G_PV_POA[k],T_PV_array[k],weather[k],other_inputs[k])`. This is *not* a required Cartesian full matrix. Only supported, explicitly mapped channels exist for a particular feeder. Unbound physical devices preserve their restored baseline; do not invent profiles.

Each binding carries source identity/hash, source channel, declared units, temporal identity, device and native property, conversion/derivation, semantic authority and versioned provenance. A source can explicitly fan out to multiple devices; no implicit device-name matching.

## 2. Load profiles (A05.2.2)

Exactly one mode is declared per exogenously bound `Load`:

1. **L1 absolute P/Q:** provide `P_i[k]` (kW) and `Q_i[k]` (kvar).
2. **L2 multiplier:** provide unitless `m_i[k]`, applying `P_i[k]=m_i[k] P_i^0` and `Q_i[k]=m_i[k] Q_i^0`. Capture the baseline pair once from the qualified, restored plant; an ordinary positive-demand load retains its baseline PF.
3. **L3 P and signed PF:** provide `P_i[k]` (kW) and `pf_i[k]`. For supported ordinary nonnegative-demand loads, `0<|pf|<=1`, compute `Q_i[k]=sign(pf_i[k]) P_i[k] tan(arccos(|pf_i[k]|))`. A negative PF means leading load demand. Disallow ambiguous negative-demand/generation interpretations unless separately qualified.

Example: with baselines `Load.House1=(100 kW,40 kvar)`, `Load.House2=(80 kW,30 kvar)`, applying a common `m=0.8` gives `(80,32)` and `(64,24)`. An unbound `Load.House3=(60,20)` remains unchanged.

Native `Load.kW`, `Load.kvar`, and `PF` setters interact. Apply the declared final P/Q pair in a qualified order with **no intermediate solve**, then read back both properties. Preserve physical load model, phases and connection. Nominal specified kW/kvar may differ from realized terminal power in voltage-dependent load models: record both distinctly.

## 3. Explicit device/group/phase mapping (A05.2.3)

- A profile may bind to one native object, several explicitly listed objects, or an explicitly declared device group.
- Each property has one authoritative writer per sample. Duplicate or conflicting writes fail during preflight unless a future separately qualified composition rule exists.
- Native multiphase `Load` aggregate kW/kvar cannot be assumed to support independent per-phase writes. Per-phase signals require actual individually qualified physical endpoints.
- Validate class, name, property, mutability, units and ownership before running; preserve unbound devices at baseline.
- Concrete CSV/Parquet/other serialization, column naming, units-conversion rules, timestamps and alignment remain A05.3 ratification items. Do not impose a sample YAML sketch as the only supported format.

## 4. PV irradiance and Faiman-style array temperature (A05.2.4)

`PVSystem.Irradiance` is incident irradiance (native kW/m^2), `Pmpp` is a preserved rated property, `%Pmpp` is a physical cap/derating percentage **not** equivalent to irradiance, and `PVSystem.kvar` remains an A04 controller action. Preserve P-T curves, inverter limits and native PV physical capability. No hidden rating changes to simulate weather.

### 4.1 Ratified temperature calculation

Where a valid, explicitly bound **outdoor/ambient temperature** and **wind-speed** series are both available for the PV, compute its present array/module temperature from the steady-state Faiman-like formula:

`T_PV_array[k] [degC] = T_outside[k] [degC] + G_POA[k] [W/m^2]/(U0 + U1 * v_wind[k] [m/s])`.

`G_POA` is plane-of-array irradiance. Conversion from the native irradiance in kW/m^2 to W/m^2 requires multiplication by `1000`; global-horizontal irradiance cannot be treated as plane-of-array irradiance without a declared, qualified transposition method. Use the same physical PV irradiance sample as that applied for this snapshot. The output drives native `PVSystem.Temperature` when that physical endpoint is qualified.

Require finite `T_outside`, `G_POA>=0`, `v_wind>=0`, `U0>0`, `U1>=0`, and strictly positive finite denominator. `U0` is in W/(m^2 K); `U1` is in W/(m^2 K)/(m/s). For zero irradiance the formula yields outdoor temperature. **Default the Faiman mode to its documented generic coefficients `U0=25.0`, `U1=6.84`**, as used by pvlib; allow user-supplied array/installation-specific overrides. Record exact coefficients and `coefficient_source=generic_faiman_default` or `user_configured` in provenance. These are empirical generic coefficients, not a validated fit for every feeder's panels. This formula is steady-state, not a thermal ODE or measured-module-temperature claim.

### 4.2 Explicit 25 degC fallback

When a **complete, explicitly bound** outside-temperature and wind-speed pair is not available for a PV, set `T_PV_array[k] = 25 degC` throughout that declared constant-temperature mode. This is the user's chosen nominal standard-reference assumption, **not** a claim that an operating module actually remains at 25 degC. Record `temperature_source=constant_25C`.

If Faiman mode is explicitly bound but a required sample is missing, duplicated, invalid or exhausted, fail closed according to A05.3. Do not silently switch to 25 degC midway through a Faiman episode. Record `temperature_source=faiman`, weather/irradiance identities and coefficients for the Faiman mode.

### 4.3 Frozen A03 semantic compatibility

Source review: A03 already registers `Load.kW` and `Load.kvar` as `STEP_EXOGENOUS`, PV availability as `Irradiance` (falling back to `pctPmpp`), and `PVSystem.kvar` as `STEP_CONTROLLABLE`. It does **not** register `PVSystem.Temperature` as `STEP_EXOGENOUS`.

Preserve A03 source byte-for-byte. Implement A05 temperature support only as a **versioned, explicitly whitelisted A05 exogenous-binding extension** justified against the actual A02/A03 inventory and native capability. Give the extension its own version/hash, preflight, unit/mode checks, and run provenance; never make it a controller action or use an unregistered permissive write. If the endpoint is not supported, fail closed. An A03 `pctPmpp` availability fallback may never receive a kW/m^2 irradiance series. Native P-T curve and temperature effects require genuine AltDSS qualification before runtime release.

## 5. Optional weather (A05.2.5)

Support optional outside air temperature, wind speed and other explicitly named physical/weather channels. A signal is either an input to a qualified plant property/derivation or separately retained for later qualified use. Merely reading weather does not alter the plant. External exogenous *truth* is distinct from A05.4 forecasts and from the A05.6 controller-visible information contract.

## 6. Missing data, units, provenance and failure (A05.2.6)

- Reject missing/duplicate/nonfinite required values, invalid units, unsupported properties/devices, conflicting targets and implicit zero fill. A deliberate absence of an optional complete weather pair is the only 25 degC fallback trigger; a malformed bound Faiman series is an error.
- A05.3 separately defines timestamp duplicate normalization, timezone/DST, interpolation, resampling, strict/tile replay and episode coverage policies; do not prematurely assume such a policy here.
- Record source hashes, device/property/phase mappings, mode, conversions, temperature derivation, qualified baseline and native readbacks, actual electrical sample timestamp and realized terminal quantities. Preserve A04 H0-H3 and FAST/STANDARD/AUDIT invariants.
- Failed required reads or property writes do not commit a history record or advance the external clock. Per A05.1, leave the episode inactive until explicit reset; do not claim rollback of native writes already made before failure.

## 7. Plant != Problem != Controller (A05.2.7)

All exogenous truth channels remain plant-input mechanisms. Setter availability is not controller action authority. P1/P2 `ProblemSpec` controls only its explicit A04 action selection, and RBC/MPC/RL cannot modify loads, irradiance or PV temperature via this exogenous writer. No model-independent lookahead through exogenous-truth objects: forecast and observation disclosure are deferred to A05.4/A05.6.

## 8. Qualification gates prior to A05 implementation freeze

1. Genuine AltDSS load L1/L2/L3 parity, readback, invalid-PF and native voltage-model distinction.
2. Explicit fan-out and per-phase supported endpoint tests, conflict/unknown device/unknown unit failures.
3. Irradiance versus `%Pmpp` semantics, preserve `Pmpp`, PV kvar authority and inverter capability.
4. Faiman hand calculations, irradiance conversion, nighttime/zero wind, coefficient provenance, complete-missing-weather 25 degC fallback, malformed bound-weather fail-closed.
5. Additive A05 PV temperature extension proven compatible with A03 frozen source and A04 action authority; reject unsupported endpoints.
6. A05.1 reset/first-step same-sample identity, Snapshot/STATIC controls, H0-H3 history and source/solution lineage.
7. Whole-predecessor byte identity plus genuine fixture integration and determinism/reproducibility regressions.

**Disposition:** A05.2.1-A05.2.7 RATIFIED with user Faiman/25 degC refinement. This is *documentation only*: no A05 runtime implementation or qualification is asserted or authorized by this package. A05.3 will ratify concrete data formats and time/replay policies.

## References

- Qualified predecessor source: `src/opendsssim/semantics/compiler.py` and A03 semantic-policy Markdown in `OpenDSSSim_A05D0_ReadOnlyInput_20261023T005006932Z.zip`.
- Faiman D. (2008), *Assessing the outdoor operating temperature of photovoltaic modules*, DOI `10.1002/pip.813`.
- Sandia PVPMC: https://pvpmc.sandia.gov/modeling-guide/2-dc-module-iv/module-temperature/faiman-module-temperature-model/
- pvlib Faiman implementation/reference: https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.temperature.faiman.html
- Native property specifications: https://dss-extensions.org/dss-format/Load.html and https://dss-extensions.org/dss-format/PVSystem.html
