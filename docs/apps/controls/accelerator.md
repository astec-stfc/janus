# Accelerator Control System

JANUS accelerator controls are generated from the accelerator definition rather than maintained as a separate control system for each machine. The source of truth is the [LAURA lattice format](https://github.com/astec-stfc/laura), which describes the sections, devices, and machine-specific control data for each supported facility. Examples of laura-lattices can be found [here](https://github.com/astec-stfc/laura-lattices)

The [SARABI](https://github.com/astec-stfc/sarabi) tooling consumes a LAURA lattice and renders the corresponding soft IOCs. JANUS uses these generated IOCs to provide both EPICS PVAccess (PVA) and Channel Access (CA) PVs for the accelerator control system.

The generated control system can therefore be reused across facilities by selecting a different LAURA lattice, without creating a separate hand-written IOC implementation for each accelerator.

### Configuration and generation

The virtual accelerator image contains the LAURA lattice repository and the SARABI tooling. During the image build it:

1. Selects the facility using `FACILITY`.
2. Copies that facility's LAURA YAML definitions into the SARABI workspace.
3. Renders the IOC records and the IOC startup configuration with SARABI.
4. Starts the generated soft IOCs through the shared virtual-accelerator service.

The lattice repository and revisions can be selected with the image build arguments `LAURA_LATTICE_REPO` and `LAURA_LATTICES_VERSION`. The SARABI and LAURA revisions are selected with `SARABI_REPO`, `SARABI_VERSION`, `LAURA_REPO`, and `LAURA_VERSION`.

See the [virtual accelerator Dockerfile](https://github.com/astec-stfc/janus/blob/develop/apps/controls/shared/virtual-accelerator/Dockerfile) for the image build flow.

### PV naming

Generated accelerator PVs retain the device names defined by the selected LAURA lattice. SARABI prepends `VM-` to the generated accelerator PV names to distinguish the simulated control system from a physical machine.

For example, a physical PV such as:

```
JFEL-S02-MAG-QUAD-01:CalcK
```

is exposed by the JANUS virtual accelerator as:

```
VM-JFEL-S02-MAG-QUAD-01:CalcK
```

The available device types and fields are determined by the selected LAURA YAML definitions and the IOC templates supported by SARABI. This includes accelerator subsystems such as magnets, cavities, BPMs, screens and cameras, and other devices represented by the lattice.

### EPICS ports

The generated IOC uses port `6090` by default in JANUS to avoid clashing with the standard Channel Access port (`5064`). Facility compose files expose the generated CA and PVA services on the configured `PORT` and `PVA_PORT` values. For example:

```
PORT=<ca-port> PVA_PORT=<pva-port> docker compose -f compose/<facility>.yml up --build ioc
```
The exact device PVs come from the selected facility's LAURA lattice and SARABI's supported templates.