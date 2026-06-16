# JANUS - Joint Accelerator Network for Unified Simulation
JANUS is a series of Docker containers that allow users to interact with simulations of accelerator components, interact with virtual IOCs for EPICS components or trigger simulations using EPICS PVs.


## `JANUS` - System Overview

The JANUS components can be grouped into the following domains:

- **Control System**
  - [Shared (EPICS, PVA)](../apps/controls/shared/) - facility-agnostic control system for simulation control. Facility-specific control system logic can be added to this directory.
- **Lattice**
  - [API](../apps/api/lattice/)
  - [Database](../apps/api/lattice/)
- **Simulation**
  - [API](../apps/api/restframe/)
  - [Engine (SIMBA)](https://github.com/astec-stfc/simba)
- **Services**
  - `epics-to-lattice` - facility specific logic to convert control system values into `Lattice` format
    - [JFEL](../services/jfel/)
  - `lattice-to-restframe` - request simulation with settings in `Lattice` format
  - `restframe-to-lattice` - submit new results in `Lattice` format to database
  - `lattice-to-epics` - update shared control system with simulation results (using `Lattice` format)

#### Figure: `JANUS` - Control System ↔ Simulation
```mermaid
flowchart RL
    %% Top Layer (External Systems)
    subgraph ControlSystem[Control System]
        IOCs
    end
    subgraph Simulation
        direction TB
        RESTFRAME[RESTFrame]
        SIMBA[SIMBA]
        ASTRA[ASTRA]
        elegant[Elegant]
        RESTFRAME ==>|6. Start Tracking| SIMBA
        SIMBA <==> |Track| ASTRA
        SIMBA <==> |Track| elegant
        SIMBA <==> |Track| ...
        SIMBA <==> |Track| Poly-lithic
    end
    subgraph Lattice
        LATTICE[Lattice API]
        DB[Lattice Database]
        LATTICE <==>|Get/Compare/Store| DB
    end
    subgraph Services
        E2L[epics-to-lattice]
        L2E[lattice-to-epics]
        L2R[lattice-to-restframe]
        R2L[restframe-to-lattice]
    end
    ControlSystem ==>|1. PV Change| E2L
    E2L ==>|2. New Settings| Lattice
    Lattice ==>|4. New Settings| L2R
    L2R ==>|5. Request Simulation| RESTFRAME
    RESTFRAME ==>|7. Simulation Finished| R2L
    R2L ==>|8. New Results| Lattice
    Lattice ==>|9. New Results| L2E
    L2E ==>|10. Update PVs| ControlSystem

    style ControlSystem fill:#4f078f,stroke:#6117a3,stroke-width:2px,color:#ffffff
    style Lattice fill:#6d157a,stroke:#a037b0,stroke-width:2px,color:#ffffff
    style Services fill:#084b8a, stroke:#4273a1, stroke-width:2px,color:#ffffff
    style Simulation fill:#8a067a, stroke:#c230b1, stroke-width:2px,color:#ffffff
    linkStyle 0,1,2,3,4,6,7,8,9 stroke:green
    linkStyle 10,11,12,13 stroke:orange

```
-----

## `JANUS` - Kafka Messaging

`JANUS` utilises the [Kafka - Python](https://kafka-python.readthedocs.io/en/master/) library to publish and consume messages via the kafka broker service. This method of orchestration allows asynchronous messaging between all containers.

The `Lattice` and `RESTFrame` APIs publish messages on the following topics:

- `Lattice`
  - `lattice_ready` - new settings have been made
  - `lattice_updated` - a previous lattice has been loaded from the database
  - `lattice_added` - a new lattice has been stored in the database
- `RESTFrame`
  - `tracking_started` - `SIMBA` tracking has started
  - `tracking finished` - `SIMBA` tracking has completed

The `Services` are responsbile for consuming those messages and acting accordingly.

`Services` subscriptions:
- `lattice-to-restframe`: `lattice_ready`
- `restframe-to-lattice`: `tracking_finished`
- `lattice-to-epics`: `lattice_updated`, `lattice_added`, `tracking_finished`

```mermaid
flowchart LR
    Lattice[Lattice]
    Kafka["Kafka Broker"]
    RESTFrame[RESTFrame]

    Lattice ==>|New Settings| Kafka
    Lattice ==>|New Results| Kafka
    Lattice ==>|Lattice Already Exists| Kafka
    RESTFrame ==>|Tracking Started| Kafka
    RESTFrame ==>|Tracking Finished| Kafka

    Kafka ==> |New Settings| lattice-to-restframe
    Kafka ==> |Tracking Started| lattice-to-epics
    Kafka ==> |Tracking Finished| restframe-to-lattice
    Kafka ==> |Lattice Already Exists| lattice-to-epics
    Kafka ==> |New Results| lattice-to-epics

    style update-PVs fill:none,stroke:none
    lattice-to-epics ==> update-PVs

    style start-tracking fill:none,stroke:none
    lattice-to-restframe ==> start-tracking

    style store-lattice fill:none,stroke:none
    restframe-to-lattice ==> store-lattice

    style Lattice fill:#6d157a,stroke:#a037b0,stroke-width:2px,color:#ffffff
    style RESTFrame fill:#8a067a, stroke:#c230b1,stroke-width:2px,color:#ffffff
    style lattice-to-restframe fill:#084b8a,stroke:#4273a1,stroke-width:2px,color:#ffffff
    style lattice-to-epics fill:#084b8a,stroke:#4273a1,stroke-width:2px,color:#ffffff
    style restframe-to-lattice fill:#084b8a,stroke:#4273a1,stroke-width:2px,color:#ffffff
    style Kafka fill:#065c10,stroke:#43944c,stroke-width:2px,color:#ffffff
```

--------

## Development Environment - Sandbox

### Overview
The `sandbox` service provides an interactive environment for working with **EPICS PVs** and JANUS-related Python tooling. It is primarily used for development, testing, and debugging.

---

### Features
- EPICS CA/PVA CLI tools (`ca/pvaget`, `ca/pvput`, `ca/pvmonitor`, etc.)
- Python environment with project dependencies ([pyepics](https://pyepics.github.io/pyepics/overview.html), [p4p](https://epics-base.github.io/p4p/index.html))
- [Jupyter Lab](https://jupyter.org/) for interactive workflows
- Non-root user (`janus-developer`)

---

### Usage
Start the sandbox:

```bash
docker compose -f docker-compose.jfel.yml up sandbox
```

Access Jupyter Lab: `http://localhost:8889`
:
- EPICS
  - `EPICS_CA_ADDR_LIST=ioc` – connects to IOC container
  - `EPICS_CA_SERVER_PORT=6090`
  - `EPICS_PVA_AUTO_ADDR_LIST=YES` - connects to physics IOC container
- Jupyter
  - Runs on port 8889
  - No authentication (dev use only)
- Volumes
  -  `sandbox/workspace → /home/janus-developer/workspace`
  - Persistent workspace for notebooks and scripts.