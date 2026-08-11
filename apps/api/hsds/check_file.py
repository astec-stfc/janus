import h5py

with h5py.File(
    "./hdf-portal/data/filestore/test_001/CLA-S02-DIA-SCR-01.openpmd.hdf5", "r"
) as f:

    ds = f["/particles/electron/momentum/x"]

    print("shape:", ds.shape)

    print("dtype:", ds.dtype)

    print("chunks:", ds.chunks)

    print("compression:", ds.compression)

    print("attrs:", dict(ds.attrs))

    print("first 10:", ds[:10])

import h5pyd

with h5pyd.File(
    "/test_001/CLA-S02-DIA-SCR-01",
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
