# JFEL to Lattice

The `jfel` service is responsible for sending changes in the EPICS control system to the [Lattice API](../apps/lattice-api.md) using the [schema](../common-schemas.md) classes.

The [jfel](https://github.com/astec-stfc/janus/blob/develop/services/jfel/) service retrieves the values of PVs for the JFEL facility and compares them with the [Lattice API](../apps/lattice-api.md) entries.

The EPICS settings are checked against entries in the [Lattice API](../apps/lattice-api.md) database. If there are no matching lattices, the settings are sent for tracking.

However, if a matching lattice is found, the uuid is sent via the kafka topic `lattice_updated` which is received by the `lattice-to-epics` message (see [shared services](shared.md) for more details).

#### JFEL to Lattice Diagram

<div class="mermaid">
flowchart LR
    API[Lattice API]
    Kafka["Kafka Broker"]
    EPICS["EPICS IOCs"]
    jfel-to-lattice["jfel-to-lattice"]
    Magnet["Quads/Dipoles"]
    Cavity["Cavities"]
    Twiss["Twiss"]
    Generator["Generator"]
    RESTFrame["RESTFrame API"]
    L2E["lattice-to-epics"]

    Magnet --> |Update| EPICS
    Cavity --> |Update| EPICS
    EPICS --> |Set Parameters| jfel-to-lattice
    Twiss --> |Set Parameters| jfel-to-lattice
    Generator --> |Set Parameters| jfel-to-lattice
    jfel-to-lattice --> |Check Settings| API
    API --> |New Settings| Kafka
    API --> |Settings Exist| Kafka
    Kafka --> |New Settings| RESTFrame
    Kafka --> |Settings Exist| L2E
</div>

### Control Parameters

The JFEL service checks the same category of control parameters as the CLARA service (RF cavities, magnets, initial Twiss, and generator settings) — see [CLARA to Lattice](clara.md#control-parameters) for the full parameter list.
