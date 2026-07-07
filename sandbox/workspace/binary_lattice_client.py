"""
Client-side utilities for fetching and decoding binary lattice data.

Usage:
    from janus_common.utils.binary_lattice_client import fetch_lattice_binary, fetch_lattice_json
    
    # Fetch as binary (efficient for large arrays)
    lattice_dict = fetch_lattice_binary("http://restframe:8000/lattice/binary")
    
    # Fallback to JSON if binary not available
    lattice_dict = fetch_lattice_json("http://api:8000/v1/lattice")
"""

import requests
import struct
import json
import numpy as np
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def _set_nested_value(root: Any, path: list[Any], value: Any) -> None:
    """Set a nested list/dict value by path, creating containers when needed."""
    current = root
    for index, part in enumerate(path[:-1]):
        next_part = path[index + 1]

        if isinstance(part, int):
            while len(current) <= part:
                current.append({} if not isinstance(next_part, int) else [])
            current = current[part]
            continue

        if part not in current or current[part] is None:
            current[part] = [] if isinstance(next_part, int) else {}
        current = current[part]

    leaf = path[-1]
    if isinstance(leaf, int):
        while len(current) <= leaf:
            current.append(None)
        current[leaf] = value
    else:
        current[leaf] = value


def fetch_lattice_binary(url: str, timeout: int = 90) -> Dict[str, Any]:
    """
    Fetch lattice data from a binary endpoint and decode it.
    
    Args:
        url: Full URL to binary lattice endpoint (e.g., http://api:8000/v1/lattice/binary)
        timeout: Request timeout in seconds
    
    Returns:
        Decoded lattice dictionary with arrays as lists
    
    Raises:
        requests.RequestException: If fetch fails
        ValueError: If binary format is invalid
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        
        binary_data = response.content
        lattice_dict = _decode_binary_lattice(binary_data)
        
        logger.info(f"Fetched lattice binary from {url}, arrays: {len(lattice_dict.get('beam_summary', {}))}")
        return lattice_dict
    except Exception as e:
        logger.error(f"Failed to fetch binary lattice from {url}: {e}")
        raise


def fetch_lattice_json(url: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Fetch lattice data from a JSON endpoint (fallback method).
    
    Args:
        url: Full URL to JSON lattice endpoint
        timeout: Request timeout in seconds
    
    Returns:
        Lattice dictionary
    
    Raises:
        requests.RequestException: If fetch fails
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        
        lattice_dict = response.json()
        logger.info(f"Fetched lattice JSON from {url}")
        return lattice_dict
    except Exception as e:
        logger.error(f"Failed to fetch JSON lattice from {url}: {e}")
        raise


def fetch_lattice_binary_metadata(url: str, timeout: int = 45) -> Dict[str, Any]:
    """
    Fetch only metadata from a binary lattice endpoint.
    
    Useful for checking array dimensions/shapes before downloading full payload.
    
    Args:
        url: Full URL to binary metadata endpoint
        timeout: Request timeout in seconds
    
    Returns:
        Metadata dict with array info
    
    Raises:
        requests.RequestException: If fetch fails
    """
    try:
        # Derive metadata URL if full URL is passed
        if url.endswith('/binary'):
            url = url + '/metadata'
        elif not url.endswith('/metadata'):
            url = url + '/binary/metadata'
        
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        
        metadata = response.json()
        logger.info(f"Fetched binary lattice metadata from {url}")
        return metadata
    except Exception as e:
        logger.error(f"Failed to fetch binary metadata from {url}: {e}")
        raise


def _decode_binary_lattice(data: bytes) -> Dict[str, Any]:
    """
    Internal function to decode binary lattice data.
    
    Format:
      [4 bytes: compression flag (0xFFFFFFFF = zstd compressed)]
      [4 bytes: metadata JSON length]
      [variable: metadata JSON]
      [variable: binary payload (array data)]
    """
    compression_flag = struct.unpack("<I", data[:4])[0]
    data = data[4:]
    
    if compression_flag == 0xFFFFFFFF:
        try:
            import zstandard as zstd
            dctx = zstd.ZstdDecompressor()
            data = dctx.decompress(data)
        except ImportError:
            logger.warning("zstandard not installed, cannot decompress binary lattice")
            raise ValueError("Lattice data is compressed but zstandard is not available")
    
    # Parse metadata
    metadata_length = struct.unpack("<I", data[:4])[0]
    metadata_json = data[4:4 + metadata_length].decode("utf-8")
    metadata = json.loads(metadata_json)
    
    payload_start = 4 + metadata_length
    payload = data[payload_start:]
    
    lattice = metadata.get("lattice_template")
    if lattice is None:
        lattice = {
            "uuid": metadata.get("lattice_uuid"),
            "facility": metadata.get("facility"),
            "client_id": metadata.get("client_id"),
            "beam_summary": {},
        }

    # Reconstruct arrays
    for array_meta in metadata.get("arrays", []):
        offset = array_meta["offset"]
        byte_length = array_meta["byte_length"]
        shape = tuple(array_meta["shape"])
        
        array_bytes = payload[offset:offset + byte_length]
        arr = np.frombuffer(array_bytes, dtype=np.float32)
        arr = arr.reshape(shape)

        path = array_meta.get("path")
        if path is None:
            path = ["beam_summary", array_meta["name"]]

        normalized_path = [int(p) if isinstance(p, str) and p.isdigit() else p for p in path]
        _set_nested_value(lattice, normalized_path, arr.tolist())

    return lattice


def compare_fetch_methods(json_url: str, binary_url: str, verbose: bool = True) -> Dict[str, Any]:
    """
    Benchmark and compare JSON vs binary fetching methods.
    
    Args:
        json_url: URL to JSON lattice endpoint
        binary_url: URL to binary lattice endpoint
        verbose: Print timing and size comparisons
    
    Returns:
        Dict with timing and payload size metrics
    """
    import time
    
    results = {}
    
    # JSON fetch
    try:
        start = time.time()
        response = requests.get(json_url, timeout=90)
        json_time = time.time() - start
        json_size = len(response.content)
        results["json"] = {"time_sec": json_time, "size_bytes": json_size}
        if verbose:
            logger.info(f"JSON: {json_time:.3f}s, {json_size / 1e6:.2f} MB")
    except Exception as e:
        logger.error(f"JSON fetch failed: {e}")
        results["json"] = {"error": str(e)}
    
    # Binary fetch
    try:
        start = time.time()
        response = requests.get(binary_url, timeout=90)
        binary_time = time.time() - start
        binary_size = len(response.content)
        results["binary"] = {"time_sec": binary_time, "size_bytes": binary_size}
        if verbose:
            logger.info(f"Binary: {binary_time:.3f}s, {binary_size / 1e6:.2f} MB")
    except Exception as e:
        logger.error(f"Binary fetch failed: {e}")
        results["binary"] = {"error": str(e)}
    
    # Compute ratios
    if "json" in results and "binary" in results and "error" not in results.get("json", {}):
        if "error" not in results.get("binary", {}):
            json_data = results["json"]
            binary_data = results["binary"]
            size_ratio = json_data["size_bytes"] / binary_data["size_bytes"]
            time_ratio = json_data["time_sec"] / binary_data["time_sec"]
            results["comparison"] = {
                "size_ratio": size_ratio,
                "time_ratio": time_ratio,
                "speedup": f"{time_ratio:.1f}x",
                "size_reduction": f"{size_ratio:.1f}x",
            }
            if verbose:
                logger.info(f"Binary is {time_ratio:.1f}x faster and {size_ratio:.1f}x smaller")
    
    return results
