#!/usr/bin/env python
"""
Binary Lattice Endpoint Diagnostic Tool
Run this to check if binary endpoints are working correctly.
"""

import sys
import struct

sys.path.insert(0, "/app")

try:
    import requests
except ImportError:
    print("ERROR: requests module not installed")
    print("Run: pip install requests")
    sys.exit(1)

print("=" * 60)
print("Binary Lattice Endpoint Diagnostic")
print("=" * 60)

# Test 1: JSON endpoint
print("\n1. Testing JSON endpoint (http://restframe:8000/lattice)...")
try:
    r = requests.get("http://restframe:8000/lattice", timeout=5)
    r.raise_for_status()
    data = r.json()
    print(f"✓ JSON endpoint working")
    print(f"  UUID: {data.get('uuid')}")
    print(f"  Facility: {data.get('facility')}")
    has_beam_summary = bool(data.get("beam_summary"))
    print(f"  BeamSummary present: {has_beam_summary}")
    if has_beam_summary:
        beam_summary = data.get("beam_summary", {})
        print(f"  BeamSummary keys: {list(beam_summary.keys())[:5]}...")
except Exception as e:
    print(f"✗ JSON endpoint failed: {e}")

# Test 2: Binary endpoint
print("\n2. Testing binary endpoint (http://restframe:8000/lattice/binary)...")
try:
    r = requests.get("http://restframe:8000/lattice/binary", timeout=5)
    r.raise_for_status()
    content = r.content
    print(f"✓ Binary endpoint responding")
    print(f"  Content-Type: {r.headers.get('Content-Type')}")
    print(f"  Response size: {len(content)} bytes")
    
    if len(content) > 0:
        print(f"  First 8 bytes (hex): {content[:8].hex()}")
        
        # Try to parse compression flag
        if len(content) >= 4:
            compression_flag = struct.unpack("<I", content[:4])[0]
            if compression_flag == 0xFFFFFFFF:
                print(f"  Format: Compressed (zstd)")
            elif compression_flag == 0:
                print(f"  Format: Uncompressed")
            else:
                print(f"  Format: Unknown (flag=0x{compression_flag:08x})")
                
        # Check Content-Type
        content_type = r.headers.get("Content-Type", "").lower()
        if "octet-stream" in content_type:
            print(f"  ✓ Correct MIME type: {content_type}")
        elif "json" in content_type:
            print(f"  ✗ WRONG MIME type (binary endpoint returning JSON): {content_type}")
        else:
            print(f"  ? Unexpected MIME type: {content_type}")
    else:
        print(f"  ✗ Empty response")
except Exception as e:
    print(f"✗ Binary endpoint failed: {e}")

# Test 3: Metadata endpoint
print("\n3. Testing metadata endpoint (http://restframe:8000/lattice/binary/metadata)...")
try:
    r = requests.get("http://restframe:8000/lattice/binary/metadata", timeout=5)
    r.raise_for_status()
    meta = r.json()
    print(f"✓ Metadata endpoint working")
    print(f"  Version: {meta.get('version')}")
    print(f"  UUID: {meta.get('lattice_uuid')}")
    arrays = meta.get("arrays", [])
    print(f"  Arrays in manifest: {len(arrays)}")
    if arrays:
        for arr in arrays[:3]:
            print(f"    - {arr['name']}: shape={arr['shape']}, size={arr['byte_length']} bytes")
        if len(arrays) > 3:
            print(f"    ... and {len(arrays) - 3} more")
except Exception as e:
    print(f"✗ Metadata endpoint failed: {e}")

# Test 4: Lattice API binary endpoint
print("\n4. Testing Lattice API binary endpoint (http://lattice-api:8000/v1/lattice/binary)...")
try:
    r = requests.get("http://lattice-api:8000/v1/lattice/binary", timeout=5)
    r.raise_for_status()
    content = r.content
    print(f"✓ Lattice API binary endpoint responding")
    print(f"  Response size: {len(content)} bytes")
    if len(content) > 0:
        print(f"  First 8 bytes (hex): {content[:8].hex()}")
except Exception as e:
    print(f"✗ Lattice API binary endpoint failed: {e}")

print("\n" + "=" * 60)
print("Diagnostic Complete")
print("=" * 60)
print("\nKey Checks:")
print("  1. JSON endpoint returns data ✓")
print("  2. Binary endpoint returns binary data (not JSON) ✓")
print("  3. Binary endpoint has octet-stream MIME type ✓")
print("  4. Metadata endpoint returns arrays ✓")
print("\nIf any fail, see BINARY_LATTICE_TROUBLESHOOTING.md")
