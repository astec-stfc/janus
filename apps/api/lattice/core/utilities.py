"""Utilities for converting between schema lattices and lattice-api ORM models.

Large beam arrays used to live as many individual ORM payload rows. The current
transport/storage path instead packs the array-bearing portion of a lattice into
the shared binary lattice format and stores that as a single payload row. The
relational ORM objects still carry the scalar/structural fields used elsewhere
in the API, while the packed payload preserves the large float arrays for lossless
round-tripping.
"""

import os
import numpy as np
import zstandard as zstd
from janus_common.schemas import elements
from core.models import (
    Lasers,
    Magnets,
    Cameras,
    Cavities,
    Markers,
    Beam,
    BPMs,
    Section,
    Sigma,
    Twiss,
    Centroid,
    Covariance,
    Intensity,
    CameraAnalysis,
    Screens,
    BeamSummary,
    Lattice,
    LatticeArrayPayload,
    InitialConditions,
    Generator,
    PhotonMonitors,
)

BEAM_ARRAY_FIELDS = ("x", "y", "z", "cpx", "cpy", "cpz")
BEAM_SUMMARY_ARRAY_FIELDS = (
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
    "centroids_x",
    "centroids_y",
    "position",
)
_ZSTD_COMPRESSOR = zstd.ZstdCompressor(level=1)
_ZSTD_DECOMPRESSOR = zstd.ZstdDecompressor()
_PACKED_LATTICE_PAYLOAD_PATH = "__lattice_binary__"
_PACKED_LATTICE_PAYLOAD_DTYPE = "binary"


def _encode_float_array(values: list[float] | None) -> tuple[bytes, int]:
    arr = np.asarray(values if values is not None else [], dtype=np.float32)
    return _ZSTD_COMPRESSOR.compress(arr.tobytes(order="C")), int(arr.size)


def _decode_float_array(payload: LatticeArrayPayload) -> list[float]:
    raw = payload.payload
    if payload.compression == "zstd":
        raw = _ZSTD_DECOMPRESSOR.decompress(raw)
    arr = np.frombuffer(raw, dtype=np.float32, count=payload.count)
    return arr.tolist()


def _append_payload(
    payload_rows: list[LatticeArrayPayload],
    path: str,
    values: list[float] | None,
) -> None:
    if values is None:
        return
    encoded, count = _encode_float_array(values)
    payload_rows.append(
        LatticeArrayPayload(
            path=path,
            dtype="float32",
            count=count,
            compression="zstd",
            payload=encoded,
        )
    )


def _make_packed_lattice_payload(lattice: elements.Lattice) -> LatticeArrayPayload:
    """Pack the full lattice into a single binary payload row.

    This replaces the per-array payload fan-out with one row so the database
    only stores a single large payload for the tracked arrays. The payload uses
    the same shared binary codec as the service-to-service transport path so the
    DB representation and HTTP representation stay aligned.
    """
    packed_bytes = lattice.to_binary(compress=True, compression_level=1)
    return LatticeArrayPayload(
        path=_PACKED_LATTICE_PAYLOAD_PATH,
        dtype=_PACKED_LATTICE_PAYLOAD_DTYPE,
        count=len(packed_bytes),
        compression="binary",
        payload=packed_bytes,
    )


def _set_beam_placeholder(beam: Beam | None) -> None:
    if beam is None:
        return
    for field_name in BEAM_ARRAY_FIELDS:
        setattr(beam, field_name, [0.0])


def _extract_beam_payloads(
    payload_rows: list[LatticeArrayPayload],
    path_prefix: str,
    source_beam: elements.Beam | None,
) -> None:
    if source_beam is None:
        return
    for field_name in BEAM_ARRAY_FIELDS:
        _append_payload(
            payload_rows,
            f"{path_prefix}.{field_name}",
            getattr(source_beam, field_name, None),
        )


def _hydrate_lattice_from_payloads(
    lattice_obj: elements.Lattice,
    payload_rows: list[LatticeArrayPayload],
) -> None:
    sections = list(lattice_obj.sections.values())
    for payload in payload_rows:
        decoded = _decode_float_array(payload)
        parts = payload.path.split(".")

        if len(parts) == 2 and parts[0] == "beam_summary":
            if lattice_obj.beam_summary is not None:
                setattr(lattice_obj.beam_summary, parts[1], decoded)
            continue

        if (
            len(parts) != 6
            or parts[0] != "sections"
            or parts[2] not in {"screens", "markers"}
            or parts[4] != "beam"
        ):
            continue

        try:
            section_idx = int(parts[1])
            element_idx = int(parts[3])
        except (TypeError, ValueError):
            continue

        if section_idx < 0 or section_idx >= len(sections):
            continue

        section = sections[section_idx]
        element_list = section.screens if parts[2] == "screens" else section.markers
        if not element_list or element_idx < 0 or element_idx >= len(element_list):
            continue

        element = element_list[element_idx]
        if element.beam is None:
            element.beam = elements.Beam()
        setattr(element.beam, parts[5], decoded)


def make_db_initial_conditions(section: elements.Section | None) -> InitialConditions:
    args = {
        "alpha_x": section.alpha_x if section else 0.0,
        "beta_x": section.beta_x if section else 0.0,
        "eta_x": section.eta_x if section else 0.0,
        "eta_xp": section.eta_xp if section else 0.0,
        "emit_x": section.emit_x if section else 0.0,
        "nemit_x": section.nemit_x if section else 0.0,
        "alpha_y": section.alpha_y if section else 0.0,
        "beta_y": section.beta_y if section else 0.0,
        "eta_y": section.eta_y if section else 0.0,
        "eta_yp": section.eta_yp if section else 0.0,
        "emit_y": section.emit_y if section else 0.0,
        "nemit_y": section.nemit_y if section else 0.0,
    }
    return InitialConditions(**args)


def make_db_generator(generator: elements.Generator | None) -> Generator:
    args = {
        "enable": generator.enable if generator else False,
        "combine_distributions": (
            generator.combine_distributions if generator else False
        ),
        "number_of_particles": generator.number_of_particles if generator else 512,
        "species": generator.species if generator else "electron",
        "probe_particle": generator.probe_particle if generator else True,
        "noise_reduction": generator.noise_reduction if generator else True,
        "cathode": generator.cathode if generator else False,
        "charge": generator.charge if generator else 0.0,
        # reference_position: float = 0.0
        "initial_momentum": generator.initial_momentum if generator else 0.0,
        "distribution_type_x": generator.distribution_type_x if generator else "g",
        "distribution_type_px": generator.distribution_type_px if generator else "g",
        "distribution_type_y": generator.distribution_type_y if generator else "g",
        "distribution_type_py": generator.distribution_type_py if generator else "g",
        "distribution_type_z": generator.distribution_type_z if generator else "g",
        "distribution_type_pz": generator.distribution_type_pz if generator else "g",
        "sigma_x": generator.sigma_x if generator else 0.0,
        "sigma_px": generator.sigma_px if generator else 0.0,
        "sigma_y": generator.sigma_y if generator else 0.0,
        "sigma_py": generator.sigma_py if generator else 0.0,
        "sigma_z": generator.sigma_z if generator else 0.0,
        "sigma_pz": generator.sigma_pz if generator else 0.0,
        "gaussian_cutoff_x": generator.gaussian_cutoff_x if generator else 3.0,
        "gaussian_cutoff_px": generator.gaussian_cutoff_px if generator else 3.0,
        "gaussian_cutoff_y": generator.gaussian_cutoff_y if generator else 3.0,
        "gaussian_cutoff_py": generator.gaussian_cutoff_py if generator else 3.0,
        "gaussian_cutoff_z": generator.gaussian_cutoff_z if generator else 3.0,
        "gaussian_cutoff_pz": generator.gaussian_cutoff_pz if generator else 3.0,
        "plateau_bunch_length": generator.plateau_bunch_length if generator else 0.0,
        "plateau_rise_time": generator.plateau_rise_time if generator else 0.0,
        "correlation_kinetic_energy": (
            generator.correlation_kinetic_energy if generator else 0.0
        ),
        "offset_x": generator.offset_x if generator else 0.0,
        "normalized_horizontal_emittance": (
            generator.normalized_horizontal_emittance if generator else 1e-6
        ),
        "correlation_px": generator.correlation_px if generator else 0.0,
        "offset_y": generator.offset_y if generator else 0.0,
        "normalized_vertical_emittance": (
            generator.normalized_vertical_emittance if generator else 1e-6
        ),
        "correlation_py": generator.correlation_py if generator else 0.0,
        "thermal_emittance": generator.thermal_emittance if generator else 0.0,
    }
    return Generator(**args)


def make_twiss() -> Twiss:
    args = {
        "alpha_x": -999.0,
        "beta_x": -999.0,
        "eta_x": -999.0,
        "eta_xp": -999.0,
        "emit_x": -999.0,
        "nemit_x": -999.0,
        "alpha_y": -999.0,
        "beta_y": -999.0,
        "eta_y": -999.0,
        "eta_yp": -999.0,
        "emit_y": -999.0,
        "nemit_y": -999.0,
    }
    return Twiss(**args)


"""Sigma"""


def make_sigma() -> Sigma:
    args = {
        "x": -999.0,
        "y": -999.0,
        "t": -999.0,
        "cp": -999.0,
        "gamma": -999.0,
    }
    return Sigma(**args)


"""Centroid"""


def make_centroid() -> Centroid:
    args = {
        "x": -999.0,
        "y": -999.0,
        "t": -999.0,
        "cp": -999.0,
        "gamma": -999.0,
        "q": -999.0,
    }
    return Centroid(**args)


"""Camera Analysis"""

"""Coveriance"""


def make_covariance() -> Covariance:
    args = {
        "xx": -999.0,
        "xxp": -999.0,
        "yy": -999.0,
        "yyp": -999.0,
        "xy": -999.0,
        "xyp": -999.0,
        "yxp": -999.0,
    }
    return Covariance(**args)


"""Intensity"""


def make_intensity() -> Intensity:
    args = {
        "min": -999.0,
        "max": -999.0,
        "mean": -999.0,
        "median": -999.0,
    }
    return Intensity(**args)


def make_analysis() -> CameraAnalysis:
    args = {
        "covariance": make_covariance(),
        "intensity": make_intensity(),
    }
    return CameraAnalysis(**args)


def fetch_generic_element_properties(element: elements.Element):
    twiss = sigma = centroid = None
    if element.twiss:
        twiss = Twiss(
            alpha_x=element.twiss.alpha_x,
            beta_x=element.twiss.beta_x,
            eta_x=element.twiss.eta_x,
            eta_xp=element.twiss.eta_xp,
            emit_x=element.twiss.emit_x,
            nemit_x=element.twiss.nemit_x,
            alpha_y=element.twiss.alpha_y,
            beta_y=element.twiss.beta_y,
            eta_y=element.twiss.eta_y,
            eta_yp=element.twiss.eta_yp,
            emit_y=element.twiss.emit_y,
            nemit_y=element.twiss.nemit_y,
        )
    if element.sigma:
        sigma = Sigma(
            x=element.sigma.x,
            y=element.sigma.y,
            t=element.sigma.t,
            cp=element.sigma.cp,
            gamma=element.sigma.gamma,
        )

    if element.centroid:
        centroid = Centroid(
            x=element.centroid.x,
            y=element.centroid.y,
            t=element.centroid.t,
            cp=element.centroid.cp,
            gamma=element.centroid.gamma,
            q=element.centroid.q or 0.0,
        )
    return twiss, sigma, centroid


def fetch_beam(element: elements.Marker | elements.Screen):
    beam = None
    if element.beam:
        beam = Beam(
            x=element.beam.x,
            y=element.beam.y,
            z=element.beam.z,
            cpx=element.beam.cpx,
            cpy=element.beam.cpy,
            cpz=element.beam.cpz,
        )
    return beam


def make_db_bpm(bpm: elements.BPM):
    twiss, sigma, centroid = fetch_generic_element_properties(bpm)

    return BPMs(
        name=bpm.name,
        type=bpm.type,
        subtype=bpm.subtype or None,
        twiss=twiss or make_twiss(),
        sigma=sigma or make_sigma(),
        centroid=centroid or make_centroid(),
        updated=bpm.updated,
    )


def make_db_photon_monitor(photon_monitor: elements.PhotonMonitor):
    twiss, sigma, centroid = fetch_generic_element_properties(photon_monitor)

    return PhotonMonitors(
        name=photon_monitor.name,
        type=photon_monitor.type,
        subtype=photon_monitor.subtype or None,
        twiss=twiss or make_twiss(),
        sigma=sigma or make_sigma(),
        centroid=centroid or make_centroid(),
        updated=photon_monitor.updated,
        intensity=photon_monitor.intensity,
    )


def make_db_cavity(cavity: elements.Cavity):
    twiss, sigma, centroid = fetch_generic_element_properties(cavity)
    return Cavities(
        name=cavity.name,
        type=cavity.type,
        subtype=cavity.subtype.name,
        twiss=twiss or make_twiss(),
        sigma=sigma or make_sigma(),
        centroid=centroid or make_centroid(),
        crest=cavity.crest,
        phase=cavity.phase,
        field_amplitude=cavity.field_amplitude,
        gradient=cavity.gradient,
        updated=cavity.updated,
    )


def make_db_magnet(magnet: elements.Magnet):
    twiss, sigma, centroid = fetch_generic_element_properties(magnet)
    return Magnets(
        name=magnet.name,
        type=magnet.type,
        subtype=magnet.subtype.name,
        twiss=twiss or make_twiss(),
        sigma=sigma or make_sigma(),
        centroid=centroid or make_centroid(),
        KnL=magnet.KnL,
        field_amplitude=magnet.field_amplitude,
        momentum=magnet.momentum,
        updated=magnet.updated,
    )


def make_db_laser(laser: elements.Laser):
    twiss, sigma, centroid = fetch_generic_element_properties(laser)
    return Lasers(
        name=laser.name,
        type=laser.type,
        subtype=laser.subtype or None,
        twiss=twiss or make_twiss(),
        sigma=sigma or make_sigma(),
        centroid=centroid or make_centroid(),
        updated=laser.updated,
    )


def make_db_camera(camera: elements.Camera):
    twiss, sigma, centroid = fetch_generic_element_properties(camera)
    return Cameras(
        name=camera.name,
        type=camera.type,
        subtype=camera.subtype or None,
        twiss=twiss or make_twiss(),
        sigma=sigma or make_sigma(),
        centroid=centroid or make_centroid(),
        analysis=make_analysis(),
    )


def make_db_screen(screen: elements.Screen):
    twiss, sigma, centroid = fetch_generic_element_properties(screen)
    beam = fetch_beam(screen)
    return Screens(
        name=screen.name,
        type=screen.type,
        subtype=screen.subtype or None,
        twiss=twiss or make_twiss(),
        sigma=sigma or make_sigma(),
        centroid=centroid or make_centroid(),
        beam=beam
        or Beam(
            x=[0.0],
            y=[0.0],
            z=[0.0],
            cpx=[0.0],
            cpy=[0.0],
            cpz=[0.0],
        ),
        updated=screen.updated,
        camera=make_db_camera(screen.camera),
        position=screen.position,
    )


def make_db_marker(marker: elements.Marker):
    twiss, sigma, centroid = fetch_generic_element_properties(marker)
    beam = fetch_beam(marker)
    return Markers(
        name=marker.name,
        type=marker.type,
        subtype=marker.subtype or None,
        twiss=twiss or make_twiss(),
        sigma=sigma or make_sigma(),
        beam=beam
        or Beam(
            x=[0.0],
            y=[0.0],
            z=[0.0],
            cpx=[0.0],
            cpy=[0.0],
            cpz=[0.0],
        ),
        centroid=centroid or make_centroid(),
        updated=marker.updated,
    )


def make_db_beam_summary(beam_summary: elements.BeamSummary):
    return BeamSummary(
        alpha_x=beam_summary.alpha_x,
        beta_x=beam_summary.beta_x,
        alpha_y=beam_summary.alpha_y,
        beta_y=beam_summary.beta_y,
        energy=beam_summary.energy,  # Assume eV
        charge=beam_summary.charge,
        n_particles=beam_summary.n_particles,  # Assume number of particles
        momentum=beam_summary.momentum,
        emittance_x=beam_summary.emittance_x,
        emittance_y=beam_summary.emittance_y,
        normalised_emittance_x=beam_summary.normalised_emittance_x,
        normalised_emittance_y=beam_summary.normalised_emittance_y,
        sigma_x=beam_summary.sigma_x,  # Assume m
        sigma_y=beam_summary.sigma_y,  # Assume m
        centroids_x=beam_summary.centroids_x,  # Assume m
        centroids_y=beam_summary.centroids_y,  # Assume m
        position=beam_summary.position,  # Assume m
    )


def convert_lattice_to_db_schema(lattice: elements.Lattice):
    """Convert a schema lattice into ORM rows.

    Scalar element data remains mapped into the relational tables, but the large
    screen/marker beam arrays and beam-summary arrays are intentionally removed
    from those ORM objects and preserved in one packed binary payload row.
    """
    if not lattice.facility:
        lattice.facility = os.getenv("FACILITY", "CLARA")
    db_sections = []
    payload_rows: list[LatticeArrayPayload] = []
    for section_idx, section in enumerate(lattice.get_sections()):
        bpm_info = cavity_info = marker_info = magnet_info = laser_info = (
            photon_monitor_info
        ) = screen_info = []
        if section.bpms:
            bpm_info = [make_db_bpm(bpm) for bpm in section.bpms]
        if section.cavities:
            cavity_info = [make_db_cavity(cavity) for cavity in section.cavities]
        if section.magnets:
            magnet_info = [make_db_magnet(magnet) for magnet in section.magnets]
        if section.markers:
            marker_info = []
            for marker_idx, marker in enumerate(section.markers):
                db_marker = make_db_marker(marker)
                marker_info.append(db_marker)
                _set_beam_placeholder(db_marker.beam)
        if section.lasers:
            laser_info = [make_db_laser(laser) for laser in section.lasers]
        if section.screens:
            screen_info = []
            for screen_idx, screen in enumerate(section.screens):
                db_screen = make_db_screen(screen)
                screen_info.append(db_screen)
                _set_beam_placeholder(db_screen.beam)
        if section.photonmonitors:
            photon_monitor_info = [
                make_db_photon_monitor(photon_monitor)
                for photon_monitor in section.photonmonitors
            ]

        db_sections.append(
            Section(
                name=section.name,
                uuid=section.uuid,
                model=section.model,
                screens=screen_info,
                bpms=bpm_info,
                cavities=cavity_info,
                magnets=magnet_info,
                markers=marker_info,
                lasers=laser_info,
                photonmonitors=photon_monitor_info,
                initial_conditions=make_db_initial_conditions(
                    section.initial_conditions
                )
                or make_db_initial_conditions(),
            )
        )
    beam_summary = None
    if lattice.beam_summary:
        beam_summary = make_db_beam_summary(lattice.beam_summary)
        for field_name in BEAM_SUMMARY_ARRAY_FIELDS:
            if hasattr(beam_summary, field_name):
                setattr(beam_summary, field_name, None)

    # Store one packed payload row instead of hundreds of per-array rows. This
    # reduces insert overhead while keeping binary reconstruction lossless.
    payload_rows = [_make_packed_lattice_payload(lattice)]

    db_lattice = Lattice(
        generator=make_db_generator(lattice.generator),
        facility=lattice.facility,
        uuid=lattice.uuid,
        sections=db_sections,
        array_payloads=payload_rows,
        beam_summary=beam_summary,
        success=lattice.success or False,
        set_initial_conditions=lattice.set_initial_conditions or "",
        client_id=lattice.client_id,
    )

    return db_lattice


def convert_db_schema_to_lattice(lattice: Lattice):
    """Convert ORM rows back into a schema lattice.

    New rows prefer the packed binary payload path. The legacy per-array payload
    hydration path is kept as a fallback so older stored lattices still decode.
    """
    if not lattice.facility:
        lattice.facility = os.getenv("FACILITY", "CLARA")

    packed_payload = next(
        (
            payload
            for payload in (lattice.array_payloads or [])
            if payload.path == _PACKED_LATTICE_PAYLOAD_PATH
        ),
        None,
    )
    if packed_payload is not None:
        # Preferred path for newly stored lattices: reconstruct directly from
        # the packed shared binary representation.
        packed_lattice = elements.Lattice.from_binary(
            packed_payload.payload,
            arrays_as_lists=False,
        )
        if not packed_lattice.facility:
            packed_lattice.facility = lattice.facility
        return packed_lattice

    beam_summary_info = None
    sections = {
        section.name: elements.Section.model_validate(
            section,
            from_attributes=True,
        )
        for section in lattice.sections
    }
    if lattice.beam_summary:
        beam_summary_info = elements.BeamSummary.model_validate(
            lattice.beam_summary,
            from_attributes=True,
        )
    uuid_ = lattice.uuid
    lattice_obj = elements.Lattice(
        generator=elements.Generator.model_validate(
            lattice.generator,
            from_attributes=True,
        ),
        facility=lattice.facility,
        sections=sections,
        beam_summary=beam_summary_info,
        uuid=uuid_,
        success=lattice.success or False,
        set_initial_conditions=lattice.set_initial_conditions or "",
        client_id=lattice.client_id,
    )
    _hydrate_lattice_from_payloads(lattice_obj, lattice.array_payloads or [])
    return lattice_obj


def convert_db_sigma_to_sigma(sigma: Sigma):
    return elements.Sigma(
        x=sigma.x,
        y=sigma.y,
        t=sigma.t,
        cp=sigma.cp,
        gamma=sigma.gamma,
    )


class LatticeManager:
    def __init__(self):
        self._current: elements.Lattice = None
        self._requests: dict = {}

    def set(self, new_lattice: elements.Lattice) -> None:
        self._current = new_lattice

    def set_request(self, request_id: str, lattice: elements.Lattice) -> None:
        self._requests[request_id] = lattice.model_copy(deep=True)

    def get(self) -> elements.Lattice:
        return self._current

    def get_request(self, request_id: str) -> elements.Lattice:
        return self._requests.get(request_id)

    def remove_request(self, request_id: str) -> None:
        self._requests.pop(request_id, None)


lattice_manager = LatticeManager()
