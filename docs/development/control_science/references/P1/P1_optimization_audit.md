# P1 Optimization / MPC Audit — Erazo-Caicedo et al.

**Status:** DAY-1 SOURCE AUDIT COMPLETE  
**Primary source:** Erazo-Caicedo, Mojica-Nava, Revelo-Fuelagán, *Model predictive control for optimal power flow in grid-connected unbalanced microgrids*, EPSR 209 (2022) 108000.  
**BibTeX key:** `erazo2022model`  
**Provided PDF:** `1-s2.0-S0378779622002267-main.pdf`

## A. Source and provenance

The uploaded full text was audited for controllable devices, renewable/storage models,
forecast use, time discretization, optimization structure, voltage limits, and IEEE-123
modifications.

## B. SOURCE — reusable science

The source models an unbalanced microgrid containing distributed generation, renewable
generation, storage, unbalanced loads, tap transformers/voltage regulation, and capacitor
banks.

It supports:
- active/reactive generator decisions;
- PV/wind apparent-power capability;
- storage dynamics;
- tap-transformer controls;
- capacitor-bank controls;
- load, market-price, and renewable forecasts;
- receding-horizon MPC;
- a 5-minute control discretization with a one-hour forecast horizon in the reported setup;
- voltage limits of 0.95–1.05 p.u.;
- a modified IEEE-123 feeder with heterogeneous DER placements.

## C. ADAPT

OpenDSSSim P1 deliberately simplifies the source formulation:

- retain regulators/taps and capacitors;
- retain PV/inverter capability;
- remove wind, diesel/conventional DG, and storage from P1 v1;
- fix PV active power to available generation;
- control only PV reactive power;
- remove economic market-price terms;
- replace the source's richer OPF/MPC with a Gurobi-compatible LinDistFlow MIQP focused on
  voltage compliance, mechanical switching, and inverter VAR effort.

## D. Forecast mapping

The source provides the principal basis for using future load and renewable information.
OpenDSSSim maps this to the common forecast tensor

`[P^L_hat, Q^L_hat, P^{PV,av}_hat]`.

The same forecast tensor is authorized for MPC and RL.

## E. Contribution to common P1

Erazo supplies the missing source support for:
- PV/inverter-based DER control;
- forecast-aware predictive control;
- unbalanced IEEE-123 DER augmentation;
- receding-horizon operation.

The exact OpenDSSSim MIQP is an adaptation, not a reproduction of the paper's full
optimization problem.
