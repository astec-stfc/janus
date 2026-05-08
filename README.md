# JANUS - Joint Accelerator Network for Unified Simulation
JANUS is a series of Docker containers that allow users to interact with simulations of accelerator components, interact with virtual IOCs for EPICS components or trigger simulations using EPICS PVs. 

*diagram here?*

## Usage

### Setup

**INSTALL GIT-LFS TO USE RPMs**

Ubuntu / WSL
------------

```
apt install git-lfs
git lfs install
```

macOS
-----

```
brew install git-lfs
git lfs install
```

Windows
-------

Install Git LFS from the official installer, then:
`git lfs install`

### Getting Started

Clone this repo including all of the relevant submodules:
```bash
git clone --recursive git@gitlab.stfc.ac.uk:janus/janus.git
```
Then navigate into the `janus` directory.

To use your host ssh-keys to clone repositories into containers, run the following:
```bash
source ./configure.sh <path-to-gitlab-ssh-key>
```

This will add your host key to an ssh-agent instance, ready to clone repositories for docker images.


🟢 **Your SSH keys will not persist past the build stage of the docker images!** 🟢


### Build
Running the following command will start all of the services in the JANUS stack. Depending on whether you're working on CLARA or ISIS will determine which of the `docker-compose<facility>.yml` files you use.  

```docker
docker compose -f docker-compose.clara.yml up --build
```
```docker
docker compose -f docker-compose.isis.yml up --build
```

To just start or run a subset you can either use the VSCode Containers extension to select the services you want to build or specify them by container name in the style below:

```docker
docker compose up -f <facility-compose-file> --build 'sandbox' 'lattice_db' 'lattice_api' 'restframe' 'lattice_to_restframe' 'restframe_to_lattice'
```

Another way to select which subset of containers you want to use is to modify the `include` statements in the docker-compose files. For example if you don't want to include the `physics-iocs` and their related services, remove this entry from the include statements. 

### Stopping the Containers

The bring the stack down, you can run:

```docker
docker compose -f <facility-compose-file> down
```

If you want to remove the postgres database tables, then you need to run

```docker
docker compose -f <facility-compose-file> down --volumes
```

### Using Different Ports
In some cases you might want to change the default port (e.g. to run multiple versions of the janus containers). In this case you will need to provide additional environment variables which you can do using the following command in Windows:
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
docker exec -it janus-sandbox-1 /bin/bash
```
#### ISIS
From inside the container run 
```bash
python -m p4p.client.cli get ISIS:SIM:SEED
```
and see it is returned as 0. This is currently the input to trigger the simulation.

Check the output of the simulation by running:
```bash
python -m p4p.client.cli get VM-MEBT-ALPHA:X
```
and see an array is returned (this may unpopulated..)

Trigger a simulation by running 
```bash
python -m p4p.client.cli put ISIS:SIM:SEED=1
```
or by doing a simple `pvput` to the same PV.

In the services terminal, see that a change is noted and a simulation is beginning to track with random settings..
After the simulation has finished, in the dev terminal, run 
```bash
python -m p4p.client.cli get VM-MEBT-ALPHA:X
```
and see it is populated or has different values to before. 

**NOTE** these PVs will be different if you're working with the CLARA implementation. 

#### CLARA
Inside the sandbox container:
```bash
caput VM-CLA-S02-MAG-QUAD-01:CalcK 0.2
caget VM-CLA-S02-DIA-BPM-02:X  # BPM-01 is before the quad so not worth checking
pvget SIM-CLA-S02-DIA-SCR-01:TWISS:Nemit_x
```
