JANUS - RESTFrame API
=====================


The [RESTFrame API](../../apps/api/restframe/) is a REST API implemented using [FastAPI](https://fastapi.tiangolo.com/).


The [RESTFrame API](../../apps/api/restframe/) provides endpoints for configuring, triggering, and querying a [SIMBA](https://github.com/astec-stfc/simba) instance within JANUS. It acts as the central interface for simulation workflows, including using beam-based surrogate models (using [Poly-lithic](https://github.com/ISISNeutronMuon/poly-lithic)).

You can access the FastAPI docs page when JANUS is running [here](http://localhost:5000/docs).

### Core Responsibilities

- Tracking simulations via `SIMBA`  
- Converting between `SIMBA` output and [Lattie schema](../../janus_common/schemas/elements.py) types 
- Managing simulation output relationships:
    - only tracking from the section that has changed
    - determining whether output already exists
- Publish tracking lifecycle events to Kafka
- Provide access to component metadata (e.g. magnets, screens, cavities) 

---

### Event Integration (Kafka)

The API publishes messages to Kafka topics to notify other services of tracking statuses:

- `tracking_started` – a lattice is being tracked using `SIMBA`
- `tracking_finished` – `SIMBA` has finished tracking and output is ready

These events enable loosely coupled interaction with downstream services such as database storage, and control systems.

---

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check / root endpoint |
| `POST` | `/new` | Create or reset a simulation instance |
| `GET` | `/lattice` | Retrieve current lattice configuration |
| `POST` | `/lattice` | Set/update lattice configuration |
| `GET` | `/uuid` | Get current tracking UUID |
| `GET` | `/info` | Retrieve object parameter(s) |
| `POST` | `/info` | Set an object parameter and return updated values |
| `POST` | `/info/json` | Set/get object properties via JSON payload |
| `GET` | `/settings` | Get current settings file |
| `POST` | `/ncpu` | Set number of CPU threads for tracking |
| `POST` | `/track` | Start tracking simulation (publishes Kafka events) |
| `GET` | `/track` | Get tracking progress and status |
| `GET` | `/results/screens` | Get list of screen names |
| `GET` | `/results/bpms` | Get list of BPM names |
| `GET` | `/results/twiss/{element}` | Get Twiss parameters for an element |
| `GET` | `/results/magnets/momentum` | Get beam momentum at magnets |
| `GET` | `/results/image/{screen}` | Get screen image (PNG) |
| `GET` | `/results/bpms/{bpm}` | Get BPM centroid positions (x, y) |
| `GET` | `/html_docs` | Render API documentation (ReDoc HTML view) 
