# JANUS - Joint Accelerator Network for Unified Simulation

JANUS is a series of Docker containers that allow users to interact with simulations of accelerator components, interact with virtual IOCs for EPICS components or trigger simulations using EPICS PVs.


## System Overview

The JANUS components can be grouped into the following domains:

- **Control System**
    - [Shared (EPICS, PVA)](apps/controls/shared.md) - facility-agnostic control system for simulation control. Facility-specific control system logic can be added to this directory.
- **Lattice**
    - [API](apps/lattice-api.md)
    - [Database](apps/lattice-api.md#lattice-database)
- **Simulation**
    - [API](apps/restframe-api.md)
    - [Engine (SIMBA)](https://github.com/astec-stfc/simba)
- **Services**
    - `epics-to-lattice` - facility specific logic to convert control system values into `Lattice` format
        - [CLARA](services/clara.md)
        - [JFEL](services/jfel.md)
    - `lattice-to-restframe` - request simulation with settings in `Lattice` format
    - `restframe-to-lattice` - submit new results in `Lattice` format to database
    - `lattice-to-epics` - update simulation control system with simulation results (using `Lattice` format)

#### Figure: Control System ↔ Simulation
<div class="mermaid">
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
      HSDS[HSDS Backend]
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
    SIMBA ==>|Output HDF5/openPMD files| HSDS
    R2L ==>|8. New Results| Lattice
    Lattice ==>|9. New Results| L2E
    L2E ==>|10. Update PVs| ControlSystem

    style ControlSystem fill:#4f078f,stroke:#6117a3,stroke-width:2px,color:#ffffff
    style Lattice fill:#6d157a,stroke:#a037b0,stroke-width:2px,color:#ffffff
    style Services fill:#084b8a, stroke:#4273a1, stroke-width:2px,color:#ffffff
    style Simulation fill:#8a067a, stroke:#c230b1, stroke-width:2px,color:#ffffff
    style HSDS fill:#065c10,stroke:#43944c,stroke-width:2px,color:#ffffff
    linkStyle 0,1,2,3,4,6,7,8,9,10 stroke:green
    linkStyle 11,12,13,14 stroke:orange
  </div>
-----

## Kafka Messaging

`JANUS` uses Kafka to publish and consume lifecycle events (e.g. `lattice_ready`, `tracking_started`) between the `Lattice`/`RESTFrame` APIs and the shared services, allowing asynchronous messaging between all containers. See [Kafka Messaging](kafka.md) for the full topic list, subscriptions, and messaging diagram.

--------

## Development Environment - Sandbox

### Overview
The `sandbox` service provides an interactive environment for working with **EPICS PVs** and JANUS-related Python tooling. It is primarily used for development, testing, and debugging.

---

### Features
- EPICS CA/PVA CLI tools (`ca/pvaget`, `ca/pvput`, `ca/pvmonitor`, etc.)
- Python environment with project dependencies ([pyepics](https://pyepics.github.io/pyepics/overview.html), [p4p](https://epics-base.github.io/p4p/index.html)) and [pycatap - for CLARA](https://projects.astec.ac.uk/pycatap/)
- [Jupyter Lab](https://jupyter.org/) for interactive workflows
- Non-root user (`janus-developer`)

---

### Usage
The sandbox is included in `stack` and `client` deployments and starts automatically with the stack. See the root `README.md` for how to start the stack.

Access Jupyter Lab: `http://localhost:8889`

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

For more information on the sandbox, visit the [docs page](./sandbox.md)