import os
import requests
import base64
import warnings
from concurrent.futures import ThreadPoolExecutor
from janus_common.utils.constants import HOST_HSDS, HSDS_PORT
import numpy as np

ROOT_URL = f"http://{HOST_HSDS}:{HSDS_PORT}"

# The backend reads a batch's arrays one after another (~15 ms each), so one
# large batch is slow. Splitting it into small per-domain batches fetched in
# parallel was ~3x faster for a full lattice (426 arrays: 9.4s -> 3.3s);
# larger batches or more than 8 workers were slower.
FETCH_BATCH_SIZE = int(os.getenv("HSDS_FETCH_BATCH_SIZE", "6"))
FETCH_WORKERS = int(os.getenv("HSDS_FETCH_WORKERS", "8"))
# dedicated pool: callers may themselves run on a thread pool, and waiting on
# a pool from inside the same pool can deadlock
_fetch_pool = ThreadPoolExecutor(max_workers=FETCH_WORKERS)

def get_dataset(domain: str, path: str) -> dict | bytes:
    url = f"{ROOT_URL}/dataset/values"
    params = {"domain": domain, "path": path}
    response = requests.get(url, params=params)
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "")
    if "application/json" in content_type:
        return response.json()
    elif "application/octet-stream" in content_type:
        return response.content
    else:
        raise ValueError(f"Unsupported content type: {content_type}")

def decode_array(array_data: bytes, dtype: str = "float64") -> list:
    array = np.frombuffer(array_data, dtype=dtype)
    return array.tolist()

def get_datasets_batch(
    named_requests: dict[str, tuple[str, str]],
) -> dict[str, bytes]:
    """Fetch named datasets in one request.

    Each result retains its request name and contains the raw dataset bytes.
    """
    url = f"{ROOT_URL}/dataset/values/batch"
    response = requests.post(url, json={"requests": named_requests})
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        warnings.warn(f"Failed to fetch datasets batch: {e}")
        return {} 
    return {
        name: base64.b64decode(data)
        for name, data in response.json().items()
    }

def decode_arrays_batch(
    named_requests: dict[str, tuple[str, str]], dtype: str = "float64"
) -> dict[str, list]:
    """Fetch and decode array datasets while retaining their request names."""
    if not named_requests:
        return {}
    raw = get_datasets_batch(named_requests)
    return {
        name: decode_array(data, dtype=dtype)
        for name, data in raw.items()
    }


def _split_by_domain(
    named_requests: dict[str, tuple[str, str]], batch_size: int
) -> list[dict[str, tuple[str, str]]]:
    """Split requests into batches of about `batch_size` arrays.

    A domain's arrays are never split across batches, so the backend still
    opens each domain only once.
    """
    by_domain: dict[str, dict[str, tuple[str, str]]] = {}
    for name, (domain, path) in named_requests.items():
        by_domain.setdefault(domain, {})[name] = (domain, path)

    batches, current = [], {}
    for group in by_domain.values():
        current.update(group)
        if len(current) >= batch_size:
            batches.append(current)
            current = {}
    if current:
        batches.append(current)
    return batches


def decode_arrays_parallel(
    named_requests: dict[str, tuple[str, str]], dtype: str = "float64"
) -> dict[str, list]:
    """Like decode_arrays_batch, but fetches small per-domain batches in parallel.

    A failed batch only loses its own arrays; the rest are still returned.
    """
    if not named_requests:
        return {}
    batches = _split_by_domain(named_requests, FETCH_BATCH_SIZE)
    decoded = {}
    for raw in _fetch_pool.map(get_datasets_batch, batches):
        decoded.update(
            (name, decode_array(data, dtype=dtype)) for name, data in raw.items()
        )
    return decoded
