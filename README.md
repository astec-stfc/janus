# JANUS - Joint Accelerator Network for Unified Simulation
JANUS is a series of Docker containers that allow users to interact with simulations of accelerator components, interact with virtual IOCs for EPICS components, or trigger simulations using EPICS PVs. 

*diagram here?*

## Usage

### Setup

Install git-lfs to use RPMs

#### Ubuntu / WSL

```
apt install git-lfs
git lfs install
```

#### macOS

```
brew install git-lfs
git lfs install
```

#### Windows

Install Git LFS from the official installer, then:
`git lfs install`

### Getting Started

Clone this repo:
```bash
git clone git@github.com:astec-stfc/janus.git
```
Then navigate into the `janus` directory.

If you want to use your host ssh-keys to clone private repositories into containers, run the following:
```bash
source ./configure.sh <path-to-gitlab/hub-ssh-key>
```

This will add your host key to an ssh-agent instance, ready to clone repositories for docker images.


🟢 **Your SSH keys will not persist past the build stage of the docker images!** 🟢


### Build

#### Local Version

Running the following command will start all the services in the JANUS stack, provided that there is a `docker-compose.<facility.lower()>.yml` file:  

```docker
make stack-up FACILITY=<facility>
```

To just start or run a subset you can either use the VSCode Containers extension to select the services you want to build or specify them by container name in the style below:

```docker
docker compose up -f <facility-compose-file> --build 'sandbox' 'lattice_db' 'lattice_api' 'restframe' 'lattice_to_restframe' 'restframe_to_lattice'
```

Another way to select which subset of containers you want to use is to modify the `include` statements in the docker-compose files. For example if you don't want to include the `physics-iocs` and their related services, remove this entry from the include statements. 

### Stopping the Containers

The bring the stack down, you can run:

```docker
make stack-down FACILITY=<facility>
```

If you want to remove the postgres database tables, then you need to run

```docker
docker compose -f <facility-compose-file> down --volumes
```

### Using Different Ports
In some cases you might want to change the default port (e.g. to run multiple versions of the JANUS containers). In this case you will need to provide additional environment variables which you can do using the following command in Windows:
```bash
$env:PORT=6010; $env:PHYSICS_PORT=6011; docker compose -f docker-compose.isis.yml up
```

To run **multiple stacks** using different ports, different 'project names' need to be provided:
```bash
$env:PORT=6010; $env:PHYSICS_PORT=6011; docker compose -f docker-compose.isis.yml -p stack1 up -d
$env:PORT=6020; $env:PHYSICS_PORT=6021; docker compose -f docker-compose.isis.yml -p stack2 up -d
```

#### Common Issues
If you get errors about the `entrypoint.sh` file not existing (which will most likely happen if you're using Windows):
```
restframe_to_lattice-1  | exec /usr/src/app/entrypoint.sh: no such file or directory
```
you may need to check that the line endings in the file are using LF not CRLF. 

### Examples
Once the stack is running, navigate into the sandbox container using the following command:
```
docker exec -it janus-stack-sandbox-1 /bin/bash
```

#### JFEL

JFEL (JANUS Free Electron Laser) is an example accelerator facility used for demonstrating the functionality of JANUS. 
It is not based on a real facility. The JFEL lattice can be cloned from [here](https://gitlab.com/astec-stfc/laura-lattices).
With only a LAURA-style lattice (including control system variables) provided, the entire JANUS stack can be built.

The following example shows how to use the sandbox container to change the quadrupole strength and check the Twiss parameters.

Inside the sandbox container:
```python
from epics import caput
from p4p.client.thread import Context
ctx = Context("pva")
caput("VM-JFEL-S02-MAG-QUAD-01:CalcK", 0.2)
# wait for the simulation to finish; you can monitor via `pvget("SIMULATION:STATUS")`
ctx.get("SIM-JFEL-S02-DIA-BPM-02:TWISS:BETA_X")  # BPM-01 is before the quad so not worth checking
ctx.get("SIM-JFEL-S02-DIA-SCR-05:TWISS:Nemit_x")
```
