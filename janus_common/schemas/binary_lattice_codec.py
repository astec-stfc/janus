"""Shared binary codec for lattice transport.

This module is the single source of truth for lattice binary serialization,
metadata manifest generation, and deserialization.

The key idea is that the JSON-like lattice structure is kept in a lightweight
metadata template while the large float arrays (screen beams, marker beams, beam
summary vectors) are lifted into a contiguous binary payload. The same format is
used for service-to-service transport and for the packed lattice payload stored
by lattice-api.
"""

from __future__ import annotations

import json
import struct
from typing import Any

import numpy as np
import zstandard as zstd


BEAM_SUMMARY_ARRAY_FIELDS = [
    "alpha_x",
    "beta_x",
    "alpha_y",
    "beta_y",
    "energy",
    "charge",
    "n_particles",
    "momentum",
    "emittance_x",
    "emittance_y",
    "normalised_emittance_x",
    "normalised_emittance_y",
    "sigma_x",
    "sigma_y",
    "sigma_t",
    "centroids_x",
    "centroids_y",
    "centroids_t",
    "position",
    "cov_xx",
    "cov_xxp",
    "cov_yy",
    "cov_yyp",
    "cov_xy",
    "cov_xyp",
]

BEAM_ARRAY_FIELDS = ["x", "y", "z", "cpx", "cpy", "cpz"]


def _field_names_with_defaults(model: Any) -> dict[str, Any]:
    if model is None:
        return {}
    return {field_name: None for field_name in BEAM_ARRAY_FIELDS if getattr(model, field_name, None) is not None}


def _beam_summary_placeholder(summary: Any) -> dict[str, Any] | None:
    if summary is None:
        return None
    return {field_name: None for field_name in BEAM_SUMMARY_ARRAY_FIELDS}


def _collect_binary_arrays_and_template_from_model(
    lattice: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    arrays: list[dict[str, Any]] = []

    lattice_template: dict[str, Any] = lattice.model_dump(
        exclude={"sections": True, "beam_summary": True}
    )

    beam_summary = getattr(lattice, "beam_summary", None)
    if beam_summary is not None:
        beam_summary_template = beam_summary.model_dump(
            exclude={field_name: True for field_name in BEAM_SUMMARY_ARRAY_FIELDS}
        )
        for field_name in BEAM_SUMMARY_ARRAY_FIELDS:
            array_data = getattr(beam_summary, field_name, None)
            if array_data is None:
                continue
            arrays.append({"path": ["beam_summary", field_name], "data": array_data})
            beam_summary_template[field_name] = None
        lattice_template["beam_summary"] = beam_summary_template

    sections_template: dict[str, Any] = {}
    sections = getattr(lattice, "sections", {}) or {}
    for section_name, section in sections.items():
        if section is None:
            sections_template[section_name] = None
            continue

        section_template: dict[str, Any] = section.model_dump(
            exclude={"screens": True, "markers": True, "beam_summary": True}
        )

        section_beam_summary = getattr(section, "beam_summary", None)
        if section_beam_summary is not None:
            section_beam_summary_template = section_beam_summary.model_dump(
                exclude={field_name: True for field_name in BEAM_SUMMARY_ARRAY_FIELDS}
            )
            for field_name in BEAM_SUMMARY_ARRAY_FIELDS:
                array_data = getattr(section_beam_summary, field_name, None)
                if array_data is None:
                    continue
                arrays.append(
                    {
                        "path": ["sections", section_name, "beam_summary", field_name],
                        "data": array_data,
                    }
                )
                section_beam_summary_template[field_name] = None
            section_template["beam_summary"] = section_beam_summary_template

        screen_templates: list[dict[str, Any]] = []
        for screen_index, screen in enumerate(section.screens or []):
            if screen is None:
                screen_templates.append(None)
                continue
            screen_template = screen.model_dump(exclude={"beam": True})
            screen_template["beam"] = _beam_summary_placeholder(screen.beam)
            beam = getattr(screen, "beam", None)
            if beam is not None:
                for field_name in BEAM_ARRAY_FIELDS:
                    array_data = getattr(beam, field_name, None)
                    if array_data is None:
                        continue
                    arrays.append(
                        {
                            "path": [
                                "sections",
                                section_name,
                                "screens",
                                screen_index,
                                "beam",
                                field_name,
                            ],
                            "data": array_data,
                        }
                    )
            screen_templates.append(screen_template)

        marker_templates: list[dict[str, Any]] = []
        for marker_index, marker in enumerate(section.markers or []):
            if marker is None:
                marker_templates.append(None)
                continue
            marker_template = marker.model_dump(exclude={"beam": True})
            marker_template["beam"] = _beam_summary_placeholder(marker.beam)
            beam = getattr(marker, "beam", None)
            if beam is not None:
                for field_name in BEAM_ARRAY_FIELDS:
                    array_data = getattr(beam, field_name, None)
                    if array_data is None:
                        continue
                    arrays.append(
                        {
                            "path": [
                                "sections",
                                section_name,
                                "markers",
                                marker_index,
                                "beam",
                                field_name,
                            ],
                            "data": array_data,
                        }
                    )
            marker_templates.append(marker_template)

        section_template["screens"] = screen_templates
        section_template["markers"] = marker_templates
        sections_template[section_name] = section_template

    lattice_template["sections"] = sections_template
    return arrays, lattice_template


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


def _construct_beam_array_metadata(section_name: str, element_index: int, element_with_beam_dict: dict[str, Any]) -> list[dict[str, Any]]:
    """Construct metadata for beam arrays in a single element."""
    arrays = []
    beam = (element_with_beam_dict or {}).get("beam") or {}
    element_type = (element_with_beam_dict.get("type") if isinstance(element_with_beam_dict, dict) else None)
    if element_type is None or not beam:
        return {}, {}
    beam_template = dict(beam) if isinstance(beam, dict) else {}
    for field_name in BEAM_ARRAY_FIELDS:
        array_data = beam.get(field_name) if isinstance(beam,dict) else None
        if array_data is not None:
            path = ["sections", section_name, f"{element_type.lower()}s", element_index, "beam", field_name]
            arrays.append({"path": path, "data": array_data})
            beam_template[field_name] = None
    return arrays, beam_template


def _collect_binary_arrays_and_template_model_aware(
    lattice: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if isinstance(lattice, dict):
        return _collect_binary_arrays_and_template(lattice)
    return _collect_binary_arrays_and_template_from_model(lattice)

def _collect_binary_arrays_and_template(lattice_dict: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Collect array entries and build lightweight lattice template without array payloads."""
    arrays: list[dict[str, Any]] = []
    # Preserve the full schema structure while replacing only the heavy float
    # arrays with ``None`` placeholders in the metadata template.
    lattice_template: dict[str, Any] = dict(lattice_dict)

    beam_summary = lattice_dict.get("beam_summary") or {}
    beam_summary_template: dict[str, Any] = dict(beam_summary) if isinstance(beam_summary, dict) else {}
    for field_name in BEAM_SUMMARY_ARRAY_FIELDS:
        array_data = beam_summary.get(field_name)
        if not array_data:
            continue
        path = ["beam_summary", field_name]
        arrays.append({"path": path, "data": array_data})
        beam_summary_template[field_name] = None
    if isinstance(beam_summary, dict):
        lattice_template["beam_summary"] = beam_summary_template

    sections = lattice_dict.get("sections") or {}
    sections_template: dict[str, Any] = {}
    for section_name, section in sections.items():
        if not isinstance(section, dict):
            sections_template[section_name] = section
            continue

        section_template: dict[str, Any] = dict(section)
        screens = (section or {}).get("screens")
        markers = (section or {}).get("markers")

        screen_templates: list[dict[str, Any]] = []
        markers_templates: list[dict[str, Any]] = []

        for screen_index, screen in enumerate(screens):
            if not isinstance(screen, dict):
                screen_templates.append(screen)
                continue
            screen_template: dict[str, Any] = dict(screen)
            array, beam_template = _construct_beam_array_metadata(section_name, screen_index, screen)
            arrays += array
            screen_template["beam"] = beam_template
            screen_templates.append(screen_template)
        for marker_index, marker in enumerate(markers):
            if not isinstance(marker, dict):
                markers_templates.append(marker)
                continue
            marker_template: dict[str, Any] = dict(marker)
            array, beam_template = _construct_beam_array_metadata(section_name, marker_index, marker)
            arrays += array
            marker_template["beam"] = beam_template
            markers_templates.append(marker_template)

        section_template["screens"] = screen_templates
        section_template["markers"] = markers_templates
        sections_template[section_name] = section_template

    if isinstance(sections, dict):
        lattice_template["sections"] = sections_template

    return arrays, lattice_template


def build_lattice_binary_metadata(lattice_dict: Any) -> dict[str, Any]:
    """Build binary metadata without generating/compressing full payload bytes."""
    arrays, lattice_template = _collect_binary_arrays_and_template_model_aware(lattice_dict)

    if isinstance(lattice_dict, dict):
        lattice_uuid = lattice_dict.get("uuid")
        facility = lattice_dict.get("facility")
        client_id = lattice_dict.get("client_id")
    else:
        lattice_uuid = getattr(lattice_dict, "uuid", None)
        facility = getattr(lattice_dict, "facility", None)
        client_id = getattr(lattice_dict, "client_id", None)

    metadata = {
        "version": 2,
        "lattice_uuid": lattice_uuid,
        "facility": facility,
        "client_id": client_id,
        "lattice_template": lattice_template,
        "arrays": [],
    }

    current_offset = 0
    for entry in arrays:
        if entry is None or not isinstance(entry, dict):
            continue
        path = entry.get("path")
        array_data = entry.get("data")
        arr = np.asarray(array_data, dtype=np.float32)
        byte_length = int(arr.size * arr.itemsize)

        metadata["arrays"].append(
            {
                "name": ".".join(str(p) for p in path),
                "path": path,
                "dtype": "float32",
                "shape": list(arr.shape),
                "offset": current_offset,
                "byte_length": byte_length,
            }
        )
        current_offset += byte_length

    return metadata


def lattice_to_binary(
    lattice_dict: Any,
    compress: bool = True,
    compression_level: int = 1,
) -> bytes:
    """Serialize a lattice dictionary into binary transport format.

    Metadata and payload are built in one pass over the collected array entries
    so the encoder does not have to resolve and convert every array twice.
    """
    arrays, lattice_template = _collect_binary_arrays_and_template_model_aware(lattice_dict)

    if isinstance(lattice_dict, dict):
        lattice_uuid = lattice_dict.get("uuid")
        facility = lattice_dict.get("facility")
        client_id = lattice_dict.get("client_id")
    else:
        lattice_uuid = getattr(lattice_dict, "uuid", None)
        facility = getattr(lattice_dict, "facility", None)
        client_id = getattr(lattice_dict, "client_id", None)

    metadata = {
        "version": 2,
        "lattice_uuid": lattice_uuid,
        "facility": facility,
        "client_id": client_id,
        "lattice_template": lattice_template,
        "arrays": [],
    }

    current_offset = 0
    payload = bytearray()
    for entry in arrays:
        if entry is None or not isinstance(entry, dict):
            continue
        path = entry.get("path")
        array_data = entry.get("data")
        arr = np.asarray(array_data, dtype=np.float32)
        byte_length = int(arr.size * arr.itemsize)

        metadata["arrays"].append(
            {
                "name": ".".join(str(p) for p in path),
                "path": path,
                "dtype": "float32",
                "shape": list(arr.shape),
                "offset": current_offset,
                "byte_length": byte_length,
            }
        )

        payload.extend(arr.tobytes())
        current_offset += byte_length

    metadata_json = json.dumps(metadata).encode("utf-8")
    metadata_length = len(metadata_json)

    result = struct.pack("<I", metadata_length) + metadata_json + payload

    if compress:
        cctx = zstd.ZstdCompressor(level=compression_level)
        result = cctx.compress(result)
        return struct.pack("<I", 0xFFFFFFFF) + result

    return struct.pack("<I", 0) + result


def binary_to_lattice(
    data: bytes,
    arrays_as_lists: bool = False,
) -> dict[str, Any]:
    """Deserialize binary lattice data back to a lattice dictionary.

    Args:
        data: Encoded binary lattice payload.
        arrays_as_lists: When True (default), materialize arrays as Python
            lists for compatibility with JSON/pydantic list fields. When False,
            keep numpy arrays to avoid ndarray->list conversion overhead.
    """
    compression_flag = struct.unpack("<I", data[:4])[0]
    data = data[4:]

    if compression_flag == 0xFFFFFFFF:
        dctx = zstd.ZstdDecompressor()
        data = dctx.decompress(data)

    metadata_length = struct.unpack("<I", data[:4])[0]
    metadata_json = data[4 : 4 + metadata_length].decode("utf-8")
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

    for array_meta in metadata.get("arrays", []):
        offset = array_meta["offset"]
        byte_length = array_meta["byte_length"]
        shape = tuple(array_meta["shape"])

        array_bytes = payload[offset : offset + byte_length]
        arr = np.frombuffer(array_bytes, dtype=np.float32).reshape(shape)
        value = arr.tolist() if arrays_as_lists else arr

        path = array_meta.get("path")
        if path is None:
            path = ["beam_summary", array_meta["name"]]

        normalized_path = [int(p) if isinstance(p, str) and p.isdigit() else p for p in path]
        _set_nested_value(lattice, normalized_path, value)

    return lattice


def get_binary_format_metadata(data: bytes) -> dict[str, Any]:
    """Extract metadata from encoded binary lattice data."""
    compression_flag = struct.unpack("<I", data[:4])[0]
    data = data[4:]

    if compression_flag == 0xFFFFFFFF:
        dctx = zstd.ZstdDecompressor()
        data = dctx.decompress(data)

    metadata_length = struct.unpack("<I", data[:4])[0]
    metadata_json = data[4 : 4 + metadata_length].decode("utf-8")
    return json.loads(metadata_json)
