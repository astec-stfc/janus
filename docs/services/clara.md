JANUS - CLARA to Lattice
========================

The `clara` service is responsible for sending changes in the EPICS control system to the [Lattice API](../../apps/api/lattice/) using the [schema](../../janus_common/schemas/) classes.

The [clara](../../services/clara/) service utilises the `pyCATAP` middle-layer to easily retrieve the values of PVs for the systems listed below and compare with the [Lattice API](../../apps/api/lattice/) entries.

The EPICS settings are checked against entries in the [Lattice API](../../apps/api/lattice/) database. If there are no matching lattices, the settings are sent for tracking.

However, if a matching lattice is found, the uuid is sent via the kafka topic `lattice_updated` which is received by the `lattice-to-epics` message (see [shared services](../services/shared.md) for more details).

#### CLARA to Lattice Diagram

```mermaid
flowchart LR
    API[Lattice API]
    Kafka["Kafka Broker"]
    CATAP["pyCATAP"]
    clara-to-lattice["clara-to-lattice"]
    Magnet["Quads/Dipoles"]
    Cavity["Cavities"]
    Twiss["Twiss"]
    Generator["Generator"]
    RESTFrame["RESTFrame API"]
    L2E["lattice-to-epics"]

    Magnet --> |Update| CATAP
    Cavity --> |Update| CATAP
    CATAP --> |Set Parameters| clara-to-lattice
    Twiss --> |Set Parameters| clara-to-lattice
    Generator --> |Set Parameters| clara-to-lattice
    clara-to-lattice --> |Check Settings| API
    API --> |New Settings| Kafka
    API --> |Settings Exist| Kafka
    Kafka --> |New Settings| RESTFrame
    Kafka --> |Settings Exist| L2E


```
### Control Parameters

The parameters that are checked for changes are:

----
#### RF Cavities
- Off Crest Phase (degrees)
- Power (MW)

----

#### Quadrupoles

- Integrated Strength -K<sub>1</sub>L (m⁻¹)

----

#### Dipoles

- Bending Angle - K<sub>0</sub>L (degrees)

----

#### Initial Twiss

- β<sub>x</sub> β<sub>y</sub>
- α<sub>x</sub> α<sub>y</sub>
- ε<sub>x</sub> ε<sub>y</sub>
- ε<sub>x</sub> ε<sub>y</sub> (Normalised)
- η<sub>x</sub> η<sub>y</sub> 
- η<sub>xρ</sub> η<sub>yρ</sub>

----

#### Generator - Beam and Particle Parameters

- Number of particles
- Species
- Charge
- Probe particle
- Cathode
- Noise reduction
- Combine distributions

#### Generator - Initial Conditions
- Initial momentum
- Kinetic‑energy correlation

#### Generator - Distribution Types
- Distribution type (x)
- Distribution type (ρ<sub>x</sub>)
- Distribution type (y)
- Distribution type (ρ<sub>y</sub>)
- Distribution type (z)
- Distribution type (ρ<sub>z</sub>)

#### Generator - RMS Beam Sizes and Moments
- σ<sub>x</sub>
- σ<sub>p x</sub>
- σ<sub>y</sub>
- σ<sub>p y</sub>
- σ<sub>z</sub>
- σ<sub>p z</sub>

#### Generator - Gaussin Cut-offs
- Gaussian cut‑off (x)
- Gaussian cut‑off (ρ<sub>x</sub>)
- Gaussian cut‑off (y)
- Gaussian cut‑off (ρ<sub>y</sub>)
- Gaussian cut‑off (z)
- Gaussian cut‑off (ρ<sub>z</sub>)

#### Generator - Offsets and Correlations
- Offset (x)
- Offset (y)
- Correlation (ρ<sub>x</sub>)
- Correlation (ρ<sub>y</sub>)

#### Generator - Emittance Parameters
- Normalised emittance ε<sub>n,x</sub>
- Normalised emittance ε<sub>n,y</sub>
- Thermal emittance