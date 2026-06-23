## Shared Schemas

The [schemas](../janus_common/schemas/elements.py) module defines the core data models used across the JANUS system.  
These schemas provide a consistent interface for exchanging lattice, beam, and control system data between APIs, services, simulation frameworks, and control systems.

All models are built using **Pydantic**, ensuring:

- Strong validation of input data  
- Consistent serialization/deserialization  
- Compatibility with FastAPI, GraphQL, and Kafka messaging  
- Clear typing for physics and control system concepts  

---

### Core Responsibilities

- Define canonical data structures for JANUS  
- Standardise data flow between services (API ↔ Kafka ↔ Simulation ↔ Controls)  
- Enforce validation rules for physics parameters  
- Provide utility methods for accessing and transforming lattice data  

---

### Schema Overview

The module is organised into **four main domains**:

---

#### Beam Physics

Models representing beam properties and phase-space data:

- `InitialConditions` – Twiss and beam parameters at `Section` start  
- `Twiss` – Optical functions (α, β, η, ε)  
- `Sigma` – Beam sizes (σₓ, σᵧ, etc.)  
- `Centroid` – Beam centroid (x, y, t, momentum)  
- `Covariance` – Beam covariance matrix components  
- `Beam` – Particle distribution arrays  
- `BeamSummary` – Evolution of beam parameters across the lattice  

---

#### Camera-Specific Attributes

Models describing measurements and image-based analysis:

- `CameraAnalysis` – Combined diagnostic output  
- `Intensity` – Image intensity statistics  

---

#### Machine Elements

Base and derived classes describing accelerator components:

- `Element` – Base class for all lattice elements  
- `BPM` – Beam position monitor  
- `Camera` – Imaging diagnostics  
- `Screen` – Beam screens linked to cameras  
- `Marker` – General measurement location  
- `Magnet` – Magnetic elements (dipole, quadrupole, sextupole, etc.)  
- `Cavity` – RF structures  
- `Laser` – Laser systems  
- `Collimator` – Beam collimation  
- `PhotonMonitor` - Photon intensity monitor for radiation sources

Each element may include:

- `twiss` – optical parameters  
- `sigma` – beam size  
- `centroid` – beam position  
- `updated` flags for control system synchronisation  

---

#### Simulation Input (Generator)

The `Generator` schema defines the **initial particle distribution** used for tracking:

- Particle properties (species, charge, momentum)  
- Transverse and longitudinal distributions  
- Beam sizes (σ) and emittance  
- Correlations and offsets  
- Distribution types (Gaussian, plateau, radial, etc.)  

Validation is enforced to ensure:

- Correct parameter combinations (e.g. σ vs flat-top distributions)  
- Physical consistency of beam definitions  

---

#### Lattice Structure

The hierarchical representation of the accelerator:

- `Section` – Logical grouping of elements  
- `Lattice` – Full machine description  

A lattice contains:

- Multiple sections  
- Machine elements within each section  
- Beam summary and generator configuration  

---


### Utility Methods

The schemas include helper methods for working with `Lattice` data:

- `get_elements()` – Retrieve all elements (optionally filtered by type)  
- `get_element(name)` – Access a specific element  
- `get_elements_dict()` – Map elements by name  
- `get_sections()` – Retrieve all sections  

These utilities simplify:

- API responses  
- GraphQL queries  
- Simulation integration  
- Control system updates  

---

### Validation and Serialization

Pydantic features are heavily used to enforce correctness:

- Field validation (`@field_validator`)  
- Model-level validation (`@model_validator`)  
- Custom serialization (`@field_serializer`)  
- Enum constraints for element subtypes  

Examples include:

- Floating-point rounding for magnet coefficients (`KnL`)  
- Validation of longitudinal distribution parameters  
- Automatic aliasing (e.g. `emit_x → ex`)  

---

### Design Principles

- **Single source of truth** for all JANUS data models  
- **Physics-aware validation** to prevent invalid configurations  
- **Extensible structure** for future elements and diagnostics  
- **Interoperability** across services and control systems  

---

### Usage

These schemas are used by:

- Lattice API (creation and retrieval)  
- GraphQL API (query filtering and results)  
- Simulation services (tracking and analysis)  
- EPICS integration (control system interaction)  
- Kafka messaging (data exchange between services)  

---

### Summary

The shared schemas form the **foundation of the JANUS data model**, ensuring that all components of the system operate on a consistent and validated representation of:

- Lattices  
- Beam physics  
- Machine elements  
- Simulation inputs  
- Diagnostics data  
