## Shared PV Support

The `janus_common/pv` package provides shared process variable (PV) utilities for JANUS.
It is the common library used to build, name, type, and handle PVs across the control and simulation services without requiring an installable package using [EPICS PVAccess (p4p)](https://epics-base.github.io/p4p/index.html).

The package contains three main modules:

- `translate.py` — metadata-driven PV generation from schema models
- `builder.py` — PV construction from Python types and pydantic fields
- `handlers.py` — PV event handlers and timestamp utilities

---

### Purpose

The `pv` package standardises how JANUS converts beam and lattice data into PVs, and how PV updates are handled.
This includes:

- generating consistent PV names for simulation and lattice metadata
- converting schema values into the correct PV types
- creating `SharedPV` instances from Python data types and enums
- updating PV timestamps and post-processing writes

---

### Module overview

#### `translate.py`

This module translates JANUS schema data into PV metadata. It is primarily used by services that publish simulation and lattice state into PVs.

Key responsibilities:

- `PVMetadata` and `PVSchemaMetadata` for representing PV names, expected types, and schema paths
- `PVSchemaMetadata.get_schema_value()` to resolve values from nested model objects
- type coercion via `value_as_type()` for bool/int/float/str/list/tuple values
- `PVTranslator` helpers for resolving pydantic annotations and normalising class names
- translator subclasses:
  - `ElementToPV`
  - `GeneratorToPV`
  - `SectionToPV`
  - `LatticeToPV`
  - `SimulationToPV`

Important behavior:

- class names such as `BeamSummary` and `InitialConditions` are normalised to PV-friendly forms like `BEAM-SUMMARY` and `INITIAL-CONDITIONS`
- nested schema attributes are traversed using the schema path stored in each metadata object
- PV metadata is generated from pydantic field annotations, including unions and enums

#### `builder.py`

This module builds `SharedPV` instances from Python type information.

Key responsibilities:

- mapping native Python types to PV native type codes via `TYPE_MAP`
- creating scalar PVs with `make_scalar_pv()`
- creating enum PVs with `make_enum_pv()`
- resolving `typing.Union`, `Literal`, and enum annotations using `resolve_single_type()`
- converting pydantic model fields into PV instances with `convert_non_native_types_to_pvs()`

Usage notes:

- `make_shared_pv_from_type()` is the central factory method used by control services to create PVs from typed fields
- `Literal` annotations are supported for both string and numeric literal sets
- enum values are exposed as choice-based PVs when the type is an `Enum`

#### `handlers.py`

This module provides PV handler classes for `SharedPV` objects.

Key responsibilities:

- `time_in_seconds_and_nanoseconds()` for PV timestamp generation
- `Handler` base class for PV operations
- `BasicHandler` for standard PV updates
- `EnumHandler` for enum PV writes and optional mapped read-back behavior

Important behavior:

- `BasicHandler` ensures update timestamps are set when the client does not provide one
- `EnumHandler` can optionally post a separate read PV value after enum changes
- `EnumHandler` supports read-only enums by rejecting writes

---

### Design principles

- **Package rooted**: the `pv` directory is designed to be mounted and imported as a package, so internal imports should use relative or package-aware paths.
- **Schema-driven**: PV metadata is generated from shared JANUS schema models rather than hard-coded PV names.
- **Minimal dependencies**: the package works with `p4p` and `pydantic` without requiring an installable wheel.
- **Consistency**: PV names, types, and timestamp handling are kept consistent for all JANUS services.

---

### Usage

This package is typically used by:

- shared control services that expose EPICS/PVA PVs
- services that convert lattice and beam schema data into PV values
- PV builders that create shared PV definitions from typed model fields

The package is imported as a package module, for example:

```python
from pv.builder import Builder
from pv.translate import LatticeToPV, ElementToPV
from pv.handlers import BasicHandler
```

If the package is mounted as a volume, imports should remain package-relative to avoid `ModuleNotFoundError` errors from bare module names.

---

### Summary

`janus_common/pv` is the shared PV support layer for JANUS. It provides:

- PV metadata generation from shared JANUS schemas
- PV construction from Python types and pydantic models
- PV event handling and timestamp management
- a consistent path for control and simulation services to expose process variables
