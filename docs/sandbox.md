# Sandbox

The JANUS sandbox is an interactive workspace for exploring simulations, accelerator data, and EPICS process variables. It is intended as a practical point of entry for users who want to inspect the running system, try Python examples, or develop small analysis scripts without changing the main JANUS services.

The sandbox is included in the stack and client deployments. It connects to the running JANUS services and uses the selected facility's control-system settings.

## Accessing the sandbox

Start JANUS using the normal deployment command for the required facility. For example, the default stack can be started with:

```bash
make stack-up FACILITY=jfel
```

Once the services are running, open Jupyter Lab at:

```text
http://localhost:8889
```

Jupyter Lab is configured for local development without a login token or password. Do not expose this endpoint outside a trusted development environment.

The sandbox workspace is mounted into the container, so files created in Jupyter Lab remain available in `sandbox/workspace` on the host. The shared `janus_common` package is also available in the workspace.

The Jupyter port can be changed with `SANDBOX_PORT`:

```bash
SANDBOX_PORT=8890 make stack-up FACILITY=jfel
```

## What is included

The sandbox provides:

- Python for analysis and scripting.
- Jupyter Lab for notebooks and interactive sessions.
- EPICS Channel Access and PVAccess client tools.
- `pyepics` for Channel Access communication.
- `p4p` for PVAccess communication.
- `requests` and JANUS utilities for calling service APIs.
- Matplotlib and related tools for plotting results.
- Facility lattice data and the shared JANUS schema utilities.

The available facilities and PV names depend on the deployment that is running. The sandbox is configured to communicate with the virtual accelerator and simulation IOC services in that deployment.

## Working with PVs

The sandbox can be used to read, monitor, and write PVs exposed by the virtual accelerator.

PV names and available fields vary by facility. The generated accelerator PVs are documented in [Accelerator Control System](apps/controls/accelerator.md), while the shared simulation and result PVs are described in [Simulation Control System](apps/controls/shared.md).

Python clients can use Channel Access and PVAccess in the same environment:

```python
from epics import caget, caput
from p4p.client.thread import Context

status = caget("SIMULATION:STATUS")
caput("VM-JFEL-S02-MAG-QUAD-01:CalcK", 0.2)

ctx = Context("pva")
beta_x = ctx.get("SIM-JFEL-S02-DIA-BPM-02:TWISS:BETA_X")
print(status, beta_x)
```

A write may trigger a simulation workflow. Allow time for tracking to complete and monitor `SIMULATION:STATUS` before reading updated result PVs.

## Exploring lattice and beam data

The sandbox can call the JANUS HTTP APIs from Python. This is useful for discovering runs, inspecting lattice metadata, and retrieving beam-array references.

For example, the service APIs can be queried with `requests`:

```python
import requests

lattice = requests.get("http://lattice_api:5000/v1/lattice/").json()
print(lattice.get("uuid"), lattice.get("facility"))
```

Beam arrays are stored by the HSDS backend. The Lattice API returns a `(domain, path)` reference for screen and marker beam data; the reference can then be used with the HSDS backend's dataset-values endpoint. See [Lattice API](apps/lattice-api.md) and [HSDS Backend](apps/hsds-backend.md) for the complete data-access workflow.

## Workspace examples

The `sandbox/workspace` directory contains example scripts and utilities for common tasks, including:

- Reading and writing accelerator PVs.
- Inspecting lattice and beam data.
- Checking service and binary-data endpoints.
- Running simple scans and plotting values.

These examples are starting points rather than required entry points. They can be copied into a notebook and adapted for the facility and run being investigated.

## Opening a shell

An interactive shell can be opened in the running container. The exact container name depends on the Compose project name; list running containers first:

```bash
docker ps --format "table {{.Names}}\t{{.Image}}"
```

Then open a shell in the sandbox container:

```bash
docker exec -it <sandbox-container> /bin/bash
```

The default working directory is `/home/janus-developer/workspace`.

## Connection settings

Inside a normal JANUS deployment, the sandbox is configured automatically. The main settings are:

| Setting | Default | Purpose |
|---|---:|---|
| `SANDBOX_PORT` | `8889` | Host port for Jupyter Lab |
| `EPICS_CA_SERVER_PORT` | `6090` | Channel Access server port |
| `EPICS_CA_ADDR_LIST` | deployment-specific | Channel Access IOC address |
| `EPICS_PVA_NAME_SERVERS` | deployment-specific | PVAccess name-server addresses |
| `EPICS_PVA_BROADCAST_PORT` | deployment-specific | PVAccess broadcast port |

Use the facility-specific deployment configuration rather than manually changing these values unless you are connecting to a separate IOC system.

## Troubleshooting

- **Jupyter Lab does not open:** confirm the sandbox container is running and check that the selected `SANDBOX_PORT` is not already in use.
- **PV commands cannot connect:** confirm the virtual accelerator and physics IOC services are running, then check the facility-specific EPICS settings.
- **A PV value is stale:** monitor `SIMULATION:STATUS` and wait for the current tracking operation to complete.
- **Beam data is unavailable:** verify that the run has completed and that the referenced HSDS domain and dataset exist.
- **A script cannot import a package:** run it inside the sandbox environment, where the JANUS and EPICS dependencies are installed.
