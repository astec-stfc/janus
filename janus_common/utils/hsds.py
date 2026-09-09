import requests
import base64
from janus_common.utils.constants import HOST_HSDS, HSDS_PORT
import numpy as np

ROOT_URL = f"http://{HOST_HSDS}:{HSDS_PORT}"

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
    response.raise_for_status()
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
