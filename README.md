# JANUS - Joint Accelerator Network for Unified Simulation

JANUS is a suite of Docker containers that allow users to interact with simulations of accelerator components, interact with virtual IOCs for EPICS components, or trigger simulations using EPICS PVs.

See [`docs/janus.md`](docs/janus.md) for a full system overview including architecture diagrams.

## Setup

### Prerequisites

Install `git-lfs` to pull RPMs tracked by Git LFS.

**Ubuntu / WSL**
```bash
apt install git-lfs
git lfs install
```

**macOS**
```bash
brew install git-lfs
git lfs install
```

**Windows**

Install Git LFS from the official installer, then run `git lfs install`.

### Clone

```bash
git clone git@github.com:astec-stfc/janus.git
cd janus
```

### SSH Keys (optional)

If any containers need to clone private repositories at build time, add your SSH key to a local agent first:

```bash
source ./configure.sh <path-to-ssh-key>
```

Your SSH key is forwarded only during the build stage and is never baked into an image.

---

## Running JANUS

JANUS provides three deployment modes, each with a corresponding `make` target.

### Stack mode — single-user local deployment

Runs the entire JANUS stack (server and client services) on a single machine. This is the recommended starting point.

```bash
make stack-up
```

To stop and remove all containers and volumes:

```bash
make stack-down
```

### Server / Client mode — distributed deployment

For multi-machine or multi-user setups, the server-side and client-side services are started separately.

**On the server machine:**
```bash
make server-up
```

**On each client machine:**
```bash
make client-up
```

To stop each side:
```bash
make server-down
make client-down
```

Client instances communicate with the server over the network. Copy `env.client1` or `env.client2` to `.env.client` and adjust `SERVER_HOST`, port assignments, and `CLIENT_ID` before starting a client. The example files show how to run two clients on the same machine without port conflicts.

### Production mode — real control system

Connects to the live facility control system instead of a virtual IOC. Uses `.env.prod` for configuration.

```bash
make prod-up
```

```bash
make prod-down
```

### Selecting a facility

`JFEL` (JANUS Free Electron Laser) is the default facility. To use a different facility, pass the `FACILITY` variable:

```bash
make stack-up FACILITY=<facility>
```

This requires a corresponding `docker-compose.<facility>.yml` file in the repository root.

---

## Configuration

Each mode reads its defaults from a corresponding env file:

| Mode       | Env file       |
|------------|----------------|
| `stack`    | `.env.stack`   |
| `client`   | `.env.client`  |
| `server`   | `.env.server`  |
| `prod`     | `.env.prod`    |

Override any variable by editing the relevant env file before running `make`.

### Running multiple stacks on the same machine

To run two stacks simultaneously without port conflicts, copy and modify the client env files provided:

- `env.client1` — default ports
- `env.client2` — shifted ports to avoid clashes with client 1

Copy the appropriate file to `.env.client` before running `make client-up`.

---

## Removing database volumes

`make stack-down` (and the other `*-down` targets) removes containers and volumes, including the Postgres lattice database. If you want to stop containers but **keep** the database, run Docker Compose directly:

```bash
docker compose -f docker-compose.jfel.yml down
```

---

## Common Issues

**`entrypoint.sh: no such file or directory` on Windows**

Line endings in `entrypoint.sh` may have been converted to CRLF. Convert them back to LF using your editor or `dos2unix`.

---

## Examples

### Sandbox

The `sandbox` service provides an interactive Python and EPICS environment for development and testing. It is included in `stack` and `client` deployments.

Access Jupyter Lab at `http://localhost:8889` once the stack is running.

To open a shell inside the sandbox container:

```bash
docker exec -it janus-stack-sandbox-1 /bin/bash
```

### JFEL — changing a quadrupole and reading Twiss parameters

Inside the sandbox container:

```python
from epics import caput
from p4p.client.thread import Context

ctx = Context("pva")
caput("VM-JFEL-S02-MAG-QUAD-01:CalcK", 0.2)
# wait for simulation to finish; monitor progress with pvget("SIMULATION:STATUS")
ctx.get("SIM-JFEL-S02-DIA-BPM-02:TWISS:BETA_X")
ctx.get("SIM-JFEL-S02-DIA-SCR-05:TWISS:Nemit_x")
```

The JFEL lattice is cloned automatically from the repository specified by `LAURA_LATTICE_REPO` (default: [astec-stfc/laura-lattices](https://github.com/astec-stfc/laura-lattices.git)) at build time.
