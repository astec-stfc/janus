# HSDS Backend

The HSDS backend provides the JANUS HTTP interface to beam data stored in [HSDS](https://www.hdfgroup.org/solutions/highly-scalable-data-service-hsds/). It is a FastAPI service backed by `h5pyd`. The service also imports HDF5 and openPMD files from the shared filestore into HSDS when RESTFrame reports that a run has finished.

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

Imports are triggered by Kafka, not by watching the filesystem:

- **`tracking_finished`** - RESTFrame publishes this once SIMBA has finished tracking and written every section's output to `/data/filestore/<uuid>/`. The backend uploads every HDF file in that folder, re-uploading any file changed since its domain was created (for example after a rerun). When all of them succeed it publishes **`hdf_folder_uploaded`** (see [Kafka Messaging](../kafka.md)).
- **Startup scan** - at startup the backend also scans all of `/data/filestore` and uploads anything missing or out of date, so runs from before the service started are picked up. The scan does not publish `hdf_folder_uploaded`.

The consumer uses the `hsds_backend` consumer group and commits its offset after each run, so runs that finish while the backend is down are uploaded when it restarts. A folder that fails to upload is retried every `HSDS_FOLDER_RETRY_SECONDS` until it succeeds and is announced.

The backend recognises files ending in:

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

`hsload` writes directly to the final domain (a prior design staged imports in a `<domain>.importing` domain and published with `hsmv`, but `hsmv`'s domain-linking rename isn't honored by this HSDS server, so it's no longer used). Readers may briefly observe a partially populated domain while a (re)import is in progress.

If `hsload` fails, the domain is removed before the next retry. Failed imports are retried with configurable backoff; a folder that still has failures is retried as a whole later, so a transient failure is not permanent.

### Linked domains

By default files are fully copied into HSDS with `hsload`. Setting `HSDS_LINK=true` switches to `hsload --link`, which uploads only metadata and chunk locations; HSDS then reads dataset values from the original file on demand. Linking requires the filestore to be mounted into the `hsds` container at `/hsds-store/<bucket>/_filestore` (read-only), matching `HSDS_LINK_ROOT`, and the source files must not be moved or modified afterwards except by a rerun, which triggers a re-upload.

Linking is off by default because h5pyd 1.0.0 / h5json 2.0.0 reject every linked contiguous dataset with `Only datasets with 'H5D_CHUNKED' layout can be resizable`, even when `maxshape` equals the shape, so every file fell back to a full copy after a wasted attempt. RESTFrame's files are small (~250 KB), so a full copy is about as fast anyway. If linking is enabled and a file can't be linked, it falls back to a full copy.

Uploads run inside the backend process, calling h5pyd's `load_file()` (what `hsload` does internally) rather than starting `hsload` for each file. Running `hsload` spent ~0.8 s per file just starting Python and importing h5py/h5pyd, several times longer than uploading one of RESTFrame's files. Each upload opens its domain with mode `w`, which overwrites a stale domain or a failed attempt, so no separate `hsrm` is needed. With 4 workers a run of ~100 files uploads in about 35 s; more workers make HSDS return `503` with its default task limits.

This relies on `h5pyd._apps.utillib.load_file`, which is not a public API; check it still matches when upgrading h5pyd.

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
| `HSDS_LINK` | `false` | Link to the source file instead of a full copy (see [Linked domains](#linked-domains)) |
| `HSDS_REQUEST_RETRIES` | `3` | Retries for each HSDS request made during an upload |
| `HSDS_LINK_ROOT` | `hsdstest/_filestore` | `<bucket>/<prefix>` where the filestore is mounted inside the `hsds` container |
| `HSDS_FOLDER_RETRY_SECONDS` | `600` | Interval for retrying folders that failed to upload |
| `BROKER_HOST` | `broker` | Kafka broker host |
| `KAFKA_PORT` | `9092` | Kafka broker port (`29092` inside the compose network) |
| `TRACKING_FINISHED_TOPIC` | `tracking_finished` | Topic that triggers a folder upload |
| `HSDS_FOLDER_UPLOADED_TOPIC` | `hdf_folder_uploaded` | Topic published when a folder is fully uploaded |
| `HSDS_CONSUMER_GROUP` | `hsds_backend` | Kafka consumer group |
| `HSDS_MAX_POLL_INTERVAL_MS` | `3600000` | Longest a single folder upload may take before Kafka reassigns the message |
| `LOG_LEVEL` | `INFO` | Backend log level |

When `HS_ENDPOINTS` is not set, the importer discovers the live SN endpoints from HSDS `/about` and distributes file imports across them. This allows `target_sn_count` to be changed without manually maintaining a port list.

HSDS itself controls the number of SN and DN nodes and request limits through its configuration, including `target_sn_count`, `target_dn_count`, `max_task_count`, and storage/cache settings.

## Operational notes

- A public domain is available only after its complete staged import is published.
- A `404` for a domain or dataset generally means the import has not completed, failed, or the supplied domain/path reference is incorrect.
- Repeated `503 Service Unavailable` responses from HSDS indicate request saturation or unavailable nodes. Reduce `HSDS_IMPORT_WORKERS` or increase HSDS resources and task capacity before increasing concurrency.
- The filestore must be mounted into the backend container at `/data/filestore`.
- Files copied into the filestore by hand (not produced by a RESTFrame run) are only imported by the startup scan.

## Source code

- [Backend application](https://github.com/astec-stfc/janus/blob/develop/apps/api/hsds/backend/app/)
- [HSDS client](https://github.com/astec-stfc/janus/blob/develop/apps/api/hsds/backend/app/services/hsds.py)
- [Synchronisation and ingestion](https://github.com/astec-stfc/janus/blob/develop/apps/api/hsds/backend/app/services/sync.py)
- [Kafka consumer](https://github.com/astec-stfc/janus/blob/develop/apps/api/hsds/backend/app/services/consumer.py)
- [HSDS configuration](https://github.com/astec-stfc/janus/blob/develop/apps/api/hsds/hsds/config.yml)
