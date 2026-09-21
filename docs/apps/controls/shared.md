# Simulation Control System

The simulation control system consists of EPICS PVAccess IOCs that serve PVs directly related to the output and control of simulations.

The `PVAccess` PVs are generated from the classes in [schemas](../../common-schemas.md) using the [translator](../../common-pv.md#translatepy) code and hosted using the [p4p](https://epics-base.github.io/p4p/index.html) python library.

----------

#### High Level PVs

There are also some high-level PVs that are created:

- `SIMULATION:STATUS` - The status of [RESTFrame](../restframe-api.md)
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

#### Lattice PVs

These PVs are generated once for each lattice:

- `SIM-LATTICE:FACILITY` - Facility name
- `SIM-LATTICE:TIMESTAMP` - Lattice timestamp
- `SIM-LATTICE:BEAM-SUMMARY:<FIELD>` - Lattice beam-summary data, including `ALPHA_X`, `ALPHA_Y`, `BETA_X`, `BETA_Y`, `ENERGY`, `MOMENTUM`, `EMITTANCE_X`, `EMITTANCE_Y`, `NORMALISED_EMITTANCE_X`, `NORMALISED_EMITTANCE_Y`, `SIGMA_X`, `SIGMA_Y`, `SIGMA_T`, `CENTROIDS_X`, `CENTROIDS_Y`, `CENTROIDS_T`, and `POSITION`

Beam-summary values are commonly arrays. The corresponding PV value is loaded from HSDS when the lattice is published.

#### Generator PVs

These PVs are generated for the lattice generator configuration. They use the `VM` prefix because they describe the virtual machine or beam generator rather than a physical lattice element:

- `VM-GENERATOR:<FIELD>` - Generator settings such as `ENABLE`, `NUMBER_OF_PARTICLES`, `SPECIES`, `CHARGE`, `PROBE_PARTICLE`, distribution types, beam sizes, Gaussian cutoffs, offsets, correlations, and emittances
- `VM-GENERATOR:ENABLE` - Whether generator changes should be applied (set to 10` to ignore or `1` to apply)


#### Section PVs

Each lattice section produces PVs using its section name:

- `SIM-<SECTION>-SIMULATION:CODE` - Simulation code/model used by the section
- `VM-<SECTION>-INITIAL-CONDITIONS:<FIELD>` - Section initial conditions, including `ALPHA_X`, `BETA_X`, `ETA_X`, `ETA_XP`, `ALPHA_Y`, `BETA_Y`, `ETA_Y`, `ETA_YP`, `EMIT_X`, `EMIT_Y`, `NEMIT_X`, and `NEMIT_Y`

For example, a section named `INJECTOR` produces `SIM-INJECTOR-SIMULATION:CODE` and `VM-INJECTOR-INITIAL-CONDITIONS:ALPHA_X`.

To use the initial conditions, you can set `VM-INITIAL-CONDITIONS:ENABLE` to a comma-seperated list of machine sections, i.e. `Linac,FEL`

#### Element PVs

Each element produces PVs using its element name:

- `SIM-<ELEMENT>:TWISS:<FIELD>` - Twiss parameters: `ALPHA_X`, `BETA_X`, `ETA_X`, `ETA_XP`, `ALPHA_Y`, `BETA_Y`, `ETA_Y`, `ETA_YP`, `EMIT_X`, `EMIT_Y`, `NEMIT_X`, and `NEMIT_Y`
- `SIM-<ELEMENT>:SIGMA:<FIELD>` - Beam standard deviations: `X`, `Y`, `T`, `CP`, and `GAMMA`
- `SIM-<ELEMENT>:CENTROID:<FIELD>` - Beam centroids: `X`, `Y`, `T`, `CP`, `GAMMA`, and `Q`
- `SIM-<ELEMENT>:BEAM:<FIELD>` - HSDS domain/path pairs for beam arrays: `X`, `Y`, `Z`, `CPX`, `CPY`, and `CPZ`

The element name is the machine-specific part of the PV, for example `SIM-JFEL-S01-DIA-SCR-01:SIGMA:X`. Beam PVs are references to array data; the control service resolves them through HSDS before publishing the array values. Element fields that are absent from a particular schema object are published using the service's missing-value handling.

-----------------