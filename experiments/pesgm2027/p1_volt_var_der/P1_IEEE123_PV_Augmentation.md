# P1 IEEE-123 PV augmentation

Patch: `OpenDSSSim_PESGM2027_P1_IEEE123_PVAugmentation_v01R1_20261012`

The canonical IEEE-123 regulator and capacitor equipment is preserved unchanged.
Only 10 PVSystem objects are added to the separate PESGM working feeder.

## Placement
Three-phase distribution PVs: buses 47, 76, 105.

Single-phase residential PVs:
20-A, 38-B, 41-C, 56-B, 70-A, 103-C, 113-A.

Residential phase allocation: A=3, B=2, C=2.

## Sizing
Canonical peak active load used for experiment sizing: 3490 kW.

- Distribution: 210 kW Pmpp / 231 kVA each.
- Residential: 10 kW Pmpp / 11 kVA each.
- Total PV Pmpp: 700 kW.
- Penetration: 20.0573%.
- Inverter oversizing: 10%.

## Capability
For each inverter:
Qmax(t) = sqrt(Srated^2 - Pav(t)^2).

At full active rating:
- distribution: 96.2341 kvar;
- residential: 4.5826 kvar.

No InvControl objects are introduced. Reactive power is reserved for the external
P1 controller contract.
