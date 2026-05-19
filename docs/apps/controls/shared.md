JANUS - Shared Control System
=============================

The shared control system consists of EPICS PVAccess IOCs that serve PVs directly related to the output and control of simulations.

The `PVAccess` PVs are generated from the classes in [schemas](../../../janus_common/schemas/) using the [translator](../../../janus_common/pv/translate.py) code and hosted using the [p4p](https://epics-base.github.io/p4p/index.html) python library.

----------

#### High Level PVs

There are also some high-level PVs that are created:

- `SIMULATION:STATUS` - The status of [RESTFrame](../../../apps/api/restframe/)
  - `COMPLETE (0)`
  - `TRACKING (1)`
  - `ERROR (2)`

- `SIMULATION:MODE` - Allows constant updating, or triggered simulations
  - `AUTO (0)`
  - `TRIGGER (1)`

- `SIMULATION:START` - When in trigger mode, starts the simulation
  - `BYPASS (0)`
  - `ACTIVATE (1)` 

- `SIMULATION:UUID` - The latest tracking uuid

-----------------