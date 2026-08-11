"""
Example: Fetching Lattice Data Efficiently

This example shows how to use the binary lattice API endpoints
for efficient transport of large arrays.

Binary Format Benefits:
- 10-100x faster than JSON
- 5-10x smaller payload
- No JSON parsing overhead
"""

import time
import importlib.util
import requests

from janus_common.utils.binary_lattice_client import (
    fetch_lattice_binary,
    fetch_lattice_json,
    fetch_lattice_binary_metadata,
    compare_fetch_methods,
)


def _has_zstandard() -> bool:
    """Return True when zstandard is available in the current Python env."""
    return importlib.util.find_spec("zstandard") is not None


def _latest_lattice_uuid(lattice_api_base: str = "http://lattice_api:5000") -> str:
    """Resolve a valid lattice UUID from the API instead of using placeholders."""
    response = requests.get(f"{lattice_api_base}/v1/lattice/uuid/latest", timeout=10)
    response.raise_for_status()
    return response.text.strip().strip('"')


# Example 1: Fetch using binary format (recommended for large arrays)
def example_fetch_binary():
    """Fetch lattice efficiently using binary format."""
    print("=" * 60)
    print("Example 1: Fetch via Binary Endpoint")
    print("=" * 60)
    
    # RESTFrame API
    restframe_url = "http://restframe:8000/lattice/binary"
    
    # Or Lattice API
    lattice_api_url = "http://lattice_api:5000/v1/lattice/binary?uuid=<lattice-uuid>"
    
    start = time.time()
    try:
        if not _has_zstandard():
            print("zstandard is not installed; using JSON fallback for this example")
            lattice_dict = fetch_lattice_json(restframe_url.replace("/binary", ""))
        else:
            lattice_dict = fetch_lattice_binary(restframe_url)
        elapsed = time.time() - start
        
        print(f"✓ Fetched lattice in {elapsed:.2f}s")
        print(f"  UUID: {lattice_dict.get('uuid')}")
        print(f"  Facility: {lattice_dict.get('facility')}")
        
        # Arrays are now available as lists
        beam_summary = lattice_dict.get("beam_summary", {})
        print(f"  Arrays in beam_summary: {len(beam_summary)}")
        
        for array_name, array_data in beam_summary.items():
            if isinstance(array_data, list):
                print(f"    - {array_name}: {len(array_data)} elements")
        
    except Exception as e:
        print(f"✗ Failed: {e}")


# Example 2: Check metadata before downloading full payload
def example_fetch_metadata():
    """Check array metadata without downloading full payload."""
    print("\n" + "=" * 60)
    print("Example 2: Fetch Metadata Only")
    print("=" * 60)
    
    restframe_url = "http://restframe:8000/lattice/binary/metadata"
    
    try:
        metadata = fetch_lattice_binary_metadata(restframe_url)
        
        print(f"✓ Fetched metadata")
        print(f"  Lattice UUID: {metadata.get('lattice_uuid')}")
        print(f"  Arrays available:")
        
        for array_info in metadata.get("arrays", []):
            size_mb = array_info["byte_length"] / 1e6
            print(f"    - {array_info['name']}: shape={array_info['shape']}, size={size_mb:.2f} MB")
        
    except Exception as e:
        print(f"✗ Failed: {e}")


# Example 3: Compare performance with JSON fallback
def example_compare_methods():
    """Compare binary vs JSON fetch performance."""
    print("\n" + "=" * 60)
    print("Example 3: Performance Comparison (Binary vs JSON)")
    print("=" * 60)
    
    json_url = "http://restframe:8000/lattice"
    binary_url = "http://restframe:8000/lattice/binary"
    
    try:
        results = compare_fetch_methods(json_url, binary_url, verbose=True)
        
        if "comparison" in results:
            print(f"\nResults:")
            print(f"  Binary is {results['comparison']['speedup']} faster")
            print(f"  Payload is {results['comparison']['size_reduction']} smaller")
    except Exception as e:
        print(f"✗ Failed: {e}")


# Example 4: Use in a service that periodically fetches lattice
def example_service_fetch():
    """Example of using binary fetch in a service."""
    print("\n" + "=" * 60)
    print("Example 4: Service Integration")
    print("=" * 60)
    
    class MyService:
        def __init__(self, api_url: str):
            self.api_url = api_url
        
        def get_lattice(self) -> dict:
            """Fetch latest lattice data efficiently."""
            try:
                # Try binary first (fast)
                return fetch_lattice_binary(self.api_url)
            except Exception as e:
                print(f"Binary fetch failed ({e}), falling back to JSON...")
                # Fallback to JSON if binary fails
                return fetch_lattice_json(self.api_url.replace("/binary", ""))
        
        def get_array_metadata(self, array_name: str = None) -> dict:
            """Get info about available arrays without downloading."""
            try:
                metadata = fetch_lattice_binary_metadata(self.api_url)
                if array_name:
                    return next(
                        (arr for arr in metadata["arrays"] if arr["name"] == array_name),
                        None
                    )
                return metadata
            except Exception as e:
                print(f"Failed to get metadata: {e}")
                return None
    
    # Usage
    service = MyService("http://restframe:8000/lattice/binary")
    
    try:
        lattice = service.get_lattice()
        print(f"✓ Service fetched lattice: {lattice.get('uuid')}")
        
        # Check specific array metadata
        energy_meta = service.get_array_metadata("energy")
        if energy_meta:
            print(f"✓ Energy array: {energy_meta['shape']} elements")
    except Exception as e:
        print(f"✗ Failed: {e}")


# Example 5: Batch fetch multiple arrays efficiently
def example_batch_fetch():
    """Fetch multiple lattice snapshots efficiently."""
    print("\n" + "=" * 60)
    print("Example 5: Batch Fetching Multiple Lattices")
    print("=" * 60)
    
    import concurrent.futures
    
    latest_uuid = _latest_lattice_uuid()
    # Fetch the same valid UUID multiple times to demonstrate parallel fetch behavior.
    lattice_uuids = [latest_uuid, latest_uuid, latest_uuid]

    use_binary = _has_zstandard()
    if not use_binary:
        print("zstandard is not installed; using JSON fallback for batch example")
    
    def fetch_one(uuid: str):
        if use_binary:
            url = f"http://lattice_api:5000/v1/lattice/binary?uuid={uuid}"
            return fetch_lattice_binary(url)
        url = f"http://lattice_api:5000/v1/lattice/?uuid={uuid}"
        return fetch_lattice_json(url)
    
    print(f"Fetching {len(lattice_uuids)} lattices in parallel...")
    
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            start = time.time()
            results = list(executor.map(fetch_one, lattice_uuids, timeout=30))
            elapsed = time.time() - start
        
        print(f"✓ Fetched {len(results)} lattices in {elapsed:.2f}s")
        total_arrays = sum(
            len(r.get("beam_summary", {})) for r in results
        )
        print(f"  Total arrays: {total_arrays}")
    except Exception as e:
        print(f"✗ Failed: {e}")


# Example 6: Inspect manifest coverage for beam_summary vs screen beam arrays
def example_manifest_screen_beam_counts():
    """Show how many Screen.beam arrays are included in binary metadata."""
    print("\n" + "=" * 60)
    print("Example 6: Metadata Coverage for Screen Beam Arrays")
    print("=" * 60)

    restframe_url = "http://restframe:8000/lattice/binary/metadata"

    try:
        metadata = fetch_lattice_binary_metadata(restframe_url)
        arrays = metadata.get("arrays", [])

        beam_summary_count = 0
        screen_beam_count = 0

        for array_info in arrays:
            path = array_info.get("path")
            if isinstance(path, list):
                if len(path) >= 2 and path[0] == "beam_summary":
                    beam_summary_count += 1
                if len(path) >= 6 and path[0] == "sections" and path[2] == "screens" and path[4] == "beam":
                    screen_beam_count += 1
            else:
                # Backward-compatible metadata fallback (v1): only beam_summary names.
                beam_summary_count += 1

        print("✓ Parsed binary metadata manifest")
        print(f"  Manifest version: {metadata.get('version', 'unknown')}")
        print(f"  Total arrays in manifest: {len(arrays)}")
        print(f"  BeamSummary arrays: {beam_summary_count}")
        print(f"  Screen.beam arrays: {screen_beam_count}")
    except Exception as e:
        print(f"✗ Failed: {e}")


if __name__ == "__main__":
    # Run all examples
    # Note: Requires running API services
    
    print("\nBinary Lattice Fetch Examples")
    print("=" * 60)
    print("Note: These require running RESTFrame/Lattice API services")
    print("       - RESTFrame API on http://restframe:8000")
    print("       - Lattice API on http://lattice_api:5000")
    print("       - With actual simulation data loaded\n")
    
    # Run individual examples
    try:
        example_fetch_binary()
    except Exception as e:
        print(f"Example 1 error: {e}\n")
    
    try:
        example_fetch_metadata()
    except Exception as e:
        print(f"Example 2 error: {e}\n")
    
    try:
        example_compare_methods()
    except Exception as e:
        print(f"Example 3 error: {e}\n")
    
    try:
        example_service_fetch()
    except Exception as e:
        print(f"Example 4 error: {e}\n")
    
    try:
        example_batch_fetch()
    except Exception as e:
        print(f"Example 5 error: {e}\n")

    try:
        example_manifest_screen_beam_counts()
    except Exception as e:
        print(f"Example 6 error: {e}\n")
    
    print("\n" + "=" * 60)
    print("Examples completed - check output above for results")
    print("=" * 60)
