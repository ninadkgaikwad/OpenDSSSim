# Fair Comparison Contract

**Status:** C0A scaffold

Within one physical control problem, all three controller paradigms must share the same:

- feeder and frozen feeder modifications;
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

Forecast access must be explicitly declared per controller.

Different information sets are allowed only when scientifically required and clearly
reported. Hidden privileged information is forbidden.

Controller-specific tuning/training/calibration data must be separated from final test
episodes according to the frozen problem contract.

The common physical problem is frozen before controller-specific equations.
