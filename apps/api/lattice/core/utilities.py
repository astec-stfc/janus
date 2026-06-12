import os
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
    InitialConditions,
    Generator,
    PhotonMonitors,
)


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
    if not lattice.facility:
        lattice.facility = os.getenv("FACILITY", "CLARA")
    db_sections = []

    for section in lattice.get_sections():
        bpm_info = cavity_info = marker_info = magnet_info = laser_info = photon_monitor_info = (
            screen_info
        ) = []
        if section.bpms:
            bpm_info = [make_db_bpm(bpm) for bpm in section.bpms]
        if section.cavities:
            cavity_info = [make_db_cavity(cavity) for cavity in section.cavities]
        if section.magnets:
            magnet_info = [make_db_magnet(magnet) for magnet in section.magnets]
        if section.markers:
            marker_info = [make_db_marker(marker) for marker in section.markers]
        if section.lasers:
            laser_info = [make_db_laser(laser) for laser in section.lasers]
        if section.screens:
            screen_info = [make_db_screen(screen) for screen in section.screens]
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
    beam_summary = (
        make_db_beam_summary(lattice.beam_summary) if lattice.beam_summary else None
    )
    db_lattice = Lattice(
        generator=make_db_generator(lattice.generator),
        facility=lattice.facility,
        uuid=lattice.uuid,
        sections=db_sections,
        beam_summary=beam_summary,
        success=lattice.success or False,
        set_initial_conditions=lattice.set_initial_conditions or "",
        client_id=lattice.client_id,
    )

    return db_lattice


def convert_db_schema_to_lattice(lattice: Lattice):
    if not lattice.facility:
        lattice.facility = os.getenv("FACILITY", "CLARA")
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
    return elements.Lattice(
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
