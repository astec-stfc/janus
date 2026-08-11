## JANUS - H5 Service

A [HSDS](https://www.hdfgroup.org/solutions/highly-scalable-data-service-hsds/) combined with file-watcher and `FastAPI` interface.

`importer` service watches for `.h5`, `.hdf5`, `.openpmd.hdf5` files uploaded to `/data/filestore` and using `hsload` to uploaded them the `hsds` service.

Domains, Groups, Datasets, and Attributes are then accessible via the `FastAPI` endpoints defined in `backend/app/main.py`

Run `docker compose -f docker-compose.yml up --build` to get started. This relies on you having created a `/data/filestore` folder that can be mounted to the `importer` service.

Copy files/folders into `/data/filestore` before or during running and they should be ingested into the hsds, ready for querying using `h5pyd` or the `FastAPI` interface provided.

### Example Query

```python
import h5pyd

with h5pyd.File(
    "/<domain>/CLA-S02-DIA-SCR-01",
    "r",
    endpoint="http://localhost:5101",
    username="admin",
    password="admin",
) as f:
    ds = f["/particles/electron/momentum/x"]
    print("shape:", ds.shape)
    print("dtype:", ds.dtype)
    print("chunks:", ds.chunks)
    print("attrs:", dict(ds.attrs))
```