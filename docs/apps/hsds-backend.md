# HSDS Backend

The HSDS backend provides the JANUS HTTP interface to beam data stored in [HSDS](https://www.hdfgroup.org/solutions/highly-scalable-data-service-hsds/). It is a FastAPI service backed by `h5pyd`. The service also watches the shared filestore and imports HDF5 and openPMD files into HSDS.

The backend has two related responsibilities:

- **Ingestion** - discover HDF5 files, load them into HSDS domains, and publish completed domains.
- **Access** - expose domain, group, dataset, attribute, and binary dataset operations through HTTP.

The Lattice API stores references to HSDS datasets rather than copying large beam arrays into its relational database. See [Lattice API - Beam Data Access](lattice-api.md#beam-data-access) for the client-facing reference workflow.

## Architecture

The service is normally deployed alongside an HSDS service:

```text
HDF5/openPMD files
        |
        v
/data/filestore  --->  hsds_backend  --->  HSDS domains and datasets
                              |
                              +--> JSON metadata and raw binary array APIs
```

The backend connects to HSDS using `HSDS_URL`, while callers connect to the backend's HTTP port. In the standard compose deployment, these are:

- HSDS: `http://hsds:5101` inside the Docker network
- HSDS backend: `http://hsds_backend:8001` inside the Docker network
- HSDS backend from the host: `http://localhost:8001`

## File ingestion

At startup, the backend starts a filesystem watcher and performs a full scan of `/data/filestore`. It recognises files ending in:

- `.hdf5`
- `.openpmd.hdf5`

Each source file becomes an HSDS domain based on its path relative to `/data/filestore`. For example:

```text
/data/filestore/<uuid>/SCREEN.openpmd.hdf5
```

becomes:

```text
/<uuid>/SCREEN
```

Parent domains are created as needed. Files are imported concurrently using the `hsload` command. The concurrency can be controlled with `HSDS_IMPORT_WORKERS`; it should be tuned against the available HSDS SN/DN resources and `max_task_count` rather than increased without limit.

### Safe publication

Imports use a private staging domain named `<domain>.importing`. The final domain is published with `hsmv` only after `hsload` completes successfully. This prevents readers from observing a domain while its groups and datasets are still being created.

If `hsload` fails, the staging domain is removed before the next retry. Failed imports are retried with configurable backoff, and the watcher periodically rescans the filestore so a transient failure is not permanent.

## HTTP API

The interactive OpenAPI documentation is available at `/docs` when the backend is running.

### Service status

```http
GET /
GET /health
```

`/` returns the service identity. `/health` reports the HSDS health status.

### Domains and groups

```http
GET /domain/?domain=/<domain>
GET /domain/exists/?domain=/<domain>
GET /group/root/?domain=/<domain>
GET /group/?domain=/<domain>&path=/<group>
GET /group/members/?domain=/<domain>&path=/<group>
```

Domain and group responses contain metadata and group members where applicable.

### Datasets and attributes

```http
GET /dataset/?domain=/<domain>&path=/<dataset>
GET /attributes/?domain=/<domain>&path=/<object>
```

These endpoints return dataset metadata and object attributes. They do not return the full array payload.

### Dataset values

Use the values endpoint when the array data itself is required:

```http
GET /dataset/values/?domain=/<domain>&path=/<dataset>
```

Vector and matrix datasets are returned as raw bytes with content type `application/octet-stream`. Optional `slice_start` and `slice_end` query parameters allow a one-dimensional range to be requested:

```http
GET /dataset/values/?domain=/<domain>&path=/<dataset>&slice_start=0&slice_end=1000
```

Scalar datasets are returned as JSON. The caller must interpret binary data using the dataset's dtype and shape; the shared JANUS utilities commonly decode beam arrays as `float64`.

### Batch values

Several arrays can be fetched in one request:

```http
POST /dataset/values/batch
Content-Type: application/json

{
  "requests": {
    "x": ["/<domain>", "/particles/electron/position/x"],
    "y": ["/<domain>", "/particles/electron/position/y"]
  }
}
```

Each request value is a two-item `(domain, path)` pair. The response maps the caller-defined names to base64-encoded binary values:

```json
{
  "x": "<base64 bytes>",
  "y": "<base64 bytes>"
}
```

Batch requests are useful when a screen or marker requires several related beam arrays. The backend opens each domain once while processing the batch.

## Configuration

The HSDS backend accepts the following main environment variables:

| Variable | Default | Purpose |
|---|---:|---|
| `HSDS_URL` | `http://hsds:5101` | HSDS service URL used by `h5pyd` |
| `HSDS_USERNAME` | unset | HSDS username |
| `HSDS_PASSWORD` | unset | HSDS password |
| `HS_ENDPOINT` | `http://hsds:5101` | Primary HSDS endpoint used by ingestion tools |
| `HS_ENDPOINTS` | unset | Optional comma-separated SN endpoint override |
| `HSDS_IMPORT_WORKERS` | `4` | Number of concurrent file imports |
| `HSDS_LOAD_MAX_RETRIES` | `5` | `hsload` attempts per file |
| `HSDS_LOAD_RETRY_BACKOFF` | `2` | Linear backoff multiplier in seconds |
| `HSDS_RESCAN_INTERVAL` | `300` | Periodic filestore rescan interval in seconds |
| `LOG_LEVEL` | `INFO` | Backend log level |

When `HS_ENDPOINTS` is not set, the importer discovers the live SN endpoints from HSDS `/about` and distributes file imports across them. This allows `target_sn_count` to be changed without manually maintaining a port list.

HSDS itself controls the number of SN and DN nodes and request limits through its configuration, including `target_sn_count`, `target_dn_count`, `max_task_count`, and storage/cache settings.

## Operational notes

- A public domain is available only after its complete staged import is published.
- A `404` for a domain or dataset generally means the import has not completed, failed, or the supplied domain/path reference is incorrect.
- Repeated `503 Service Unavailable` responses from HSDS indicate request saturation or unavailable nodes. Reduce `HSDS_IMPORT_WORKERS` or increase HSDS resources and task capacity before increasing concurrency.
- The filestore must be mounted into the backend container at `/data/filestore`.
- Source files should be fully written before they are made visible to the watcher; importing a file that is still being copied can fail or produce an incomplete source read.

## Source code

- [Backend application](https://github.com/astec-stfc/janus/blob/develop/apps/api/hsds/backend/app/)
- [HSDS client](https://github.com/astec-stfc/janus/blob/develop/apps/api/hsds/backend/app/services/hsds.py)
- [Synchronisation and ingestion](https://github.com/astec-stfc/janus/blob/develop/apps/api/hsds/backend/app/services/sync.py)
- [Filesystem watcher](https://github.com/astec-stfc/janus/blob/develop/apps/api/hsds/backend/app/services/watcher.py)
- [HSDS configuration](https://github.com/astec-stfc/janus/blob/develop/apps/api/hsds/hsds/config.yml)
