JANUS - CLARA Control System
============================

The CLARA control system is an EPICS Channel Access based control system that runs a soft IOC meant to mimic the real CLARA control system PVs.

The [ioc](../../../apps/controls/clara/ioc/) image is built from the [epics-base](../../../apps/controls/clara/epics_base/) image and builds the records for the following systems:

- BPMs
- Cameras
- Machine Interlocks
- Laser Subsystems (shutters, mirrors, attenuators, diagnostics)
- Magnets
- RF Cavities
- RF Modulators
- Vacuum (values and gauges)
- Water Cooling

All PVs in this control system are prepended with `VM-` to avoid clashing with the physical control system.
For example, if the PV for a physical magnet current on CLARA would be `CLA-S02-MAG-QUAD-01:READI`, it would be `VM-CLA-S02-MAG-QUAD-01:READI`.

For JANUS, the CLARA `ioc` service uses `6090` as the `EPICS_CA_SERVER_PORT` by default. This is to avoid the default port for EPICS channel access (`5064`) and any clashing that would result from that. 

However, this can be set by using:

```
PORT=<port-number> docker compose up -f docker-compose.clara.yml up --build ioc
```
---------

### Control PVs for JANUS

The details of all PVs for devices can be found in the [CLARA LAURA lattice](https://gitlab.stfc.ac.uk/xkc85723/laura-lattices/-/tree/main/CLARA/YAML?ref_type=heads)

------

<details>
<summary><strong>Magnets</strong></summary>

[CLARA Magnets - LAURA](https://gitlab.stfc.ac.uk/xkc85723/laura-lattices/-/tree/main/CLARA/YAML/Magnet?ref_type=heads)

These prefixes are generally the PVs are used to affect magnets in JANUS, and should go after the device name i.e. `VM-CLA-S02-MAG-QUAD-01:CalcK` 

- `SPOWER` - set power supply on/off
- `RPOWER` - readback power supply on/off
- `SETI` - current setpoint
- `READI` - current readback
- `CalcK` - strength readback
- `SETK` - strength setpoint

</details>

---------------------

<details>
<summary><strong>Cavities</strong></summary>

[CLARA Cavities - LAURA](https://gitlab.stfc.ac.uk/xkc85723/laura-lattices/-/tree/main/CLARA/YAML/RF?ref_type=heads)

These prefixes are generally the PVs are used to affect cavities in JANUS, and should go after the device name i.e. `VM-CLA-L01-RF-CTRL-01:setPower` 

- `getPower` - readback for cavity power (in MW)
- `setPower` - setpoint for cavity power (in MW)
- `setPhase` - setpoint for phase (in degrees)
- `getPhase` - readback for phase (in degrees)
- `PHASE_C` - setpoint for crest phase (in degrees)
- `PHASE_OFF` - setpoint for off-crest phase (in degrees)
- `getCrestPhase` - readback for off-crest phase (sorry about the naming...)

</details>

-----