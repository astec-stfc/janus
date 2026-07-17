"""GraphQL schema definitions for lattice queries"""

from typing import Optional, List
import strawberry


@strawberry.input
class TwissRangeInput:
    """Twiss parameters for lattice elements"""

    alpha_x_range: Optional[List[float]] = None
    beta_x_range: Optional[List[float]] = None
    alpha_y_range: Optional[List[float]] = None
    beta_y_range: Optional[List[float]] = None
    eta_x_range: Optional[List[float]] = None
    eta_xp_range: Optional[List[float]] = None
    eta_y_range: Optional[List[float]] = None
    eta_yp_range: Optional[List[float]] = None
    emit_x_range: Optional[List[float]] = None
    emit_y_range: Optional[List[float]] = None
    nemit_x_range: Optional[List[float]] = None
    nemit_y_range: Optional[List[float]] = None
    element_name: str


@strawberry.input
class TwissInput:
    """Twiss parameters for lattice elements"""

    alpha_x: float = 0.0
    beta_x: float = 0.0
    alpha_y: float = 0.0
    beta_y: float = 0.0
    eta_x: float = 0.0
    eta_xp: float = 0.0
    eta_y: float = 0.0
    eta_yp: float = 0.0
    emit_x: float = 0.0
    emit_y: float = 0.0
    nemit_x: float = 0.0
    nemit_y: float = 0.0
    element_name: str


@strawberry.input
class InitialConditionsInput:
    """Initial conditions for lattice sections"""

    alpha_x: float = 0.0
    beta_x: float = 0.0
    alpha_y: float = 0.0
    beta_y: float = 0.0
    eta_x: float = 0.0
    eta_xp: float = 0.0
    eta_y: float = 0.0
    eta_yp: float = 0.0
    emit_x: float = 0.0
    emit_y: float = 0.0
    nemit_x: float = 0.0
    nemit_y: float = 0.0


@strawberry.input
class SigmaRangeInput:
    """Sigmas for lattice elements"""

    x_range: Optional[List[float]] = None
    y_range: Optional[List[float]] = None
    t_range: Optional[List[float]] = None
    cp_range: Optional[List[float]] = None
    gamma_range: Optional[List[float]] = None
    element_name: str


@strawberry.input
class SigmaInput:
    """Sigmas for lattice elements"""

    x: float = 0.0
    y: float = 0.0
    t: float = 0.0
    cp: float = 0.0
    gamma: float = 0.0
    element_name: str


@strawberry.input
class CentroidInput:
    """Centroid information for lattice elements"""

    x: float = 0.0
    y: float = 0.0
    t: float = 0.0
    cp: float = 0.0
    gamma: float = 0.0
    q: float = 0.0


@strawberry.input
class ElementInput:
    """Element Information"""

    name: str
    type: Optional[str] = ""
    length: Optional[float] = 0.0
    subtype: Optional[str] = None
    twiss: Optional[TwissRangeInput] = None
    sigma: Optional[SigmaRangeInput] = None
    centroid: Optional[CentroidInput] = None
    updated: bool = False


@strawberry.input
class MagnetRangeInput(ElementInput):
    """Input type for partial magnet filtering"""

    section: Optional[str] = None
    k_range: Optional[List[float]] = None
    field_amplitude: Optional[float] = None
    momentum: Optional[float] = None

    @property
    def angle(self) -> Optional[float]:
        """Calculate angle for dipole magnets"""
        if self.KnL and len(self.KnL) > 0:
            return self.KnL[0]
        return None

    @property
    def k1l(self) -> Optional[float]:
        """Calculate k1l for quadrupole magnets"""
        if self.KnL and len(self.KnL) > 1:
            return self.KnL[1]
        return None

    @property
    def k2l(self) -> Optional[float]:
        """Calculate k2l for sextupole magnets"""
        if self.KnL and len(self.KnL) > 2:
            return self.KnL[2]
        return None


@strawberry.input
class MagnetInput(ElementInput):
    """Input type for magnet filtering"""

    section: Optional[str] = None
    KnL: Optional[List[float]] = None
    field_amplitude: Optional[float] = None
    momentum: Optional[float] = None


@strawberry.input
class CavityRangeInput(ElementInput):
    """Input type for partial cavity filtering"""

    field_amplitude_range: Optional[List[float]] = None
    phase_range: Optional[List[float]] = None
    crest_range: Optional[List[float]] = None
    gradient_range: Optional[List[float]] = None


@strawberry.input
class CavityInput(ElementInput):
    """Input type for cavity filtering"""

    field_amplitude: Optional[float] = None
    phase: Optional[float] = None
    crest: Optional[float] = None
    gradient: Optional[float] = None


@strawberry.input
class SectionInput:
    """Input type for partial section filtering"""

    name: Optional[str] = None
    model: Optional[str] = None
    initial_conditions: Optional[InitialConditionsInput] = None


@strawberry.input
class GeneratorInput:
    enable: Optional[bool] = None
    combine_distributions: Optional[bool] = None
    number_of_particles: Optional[int] = None
    species: Optional[str] = None
    probe_particle: Optional[bool] = None
    noise_reduction: Optional[bool] = None
    cathode: Optional[bool] = None
    charge: Optional[float] = None
    # reference_position: float = 0.0
    initial_momentum: Optional[float] = None
    distribution_type_x: Optional[str] = None
    distribution_type_px: Optional[str] = None
    distribution_type_y: Optional[str] = None
    distribution_type_py: Optional[str] = None
    distribution_type_z: Optional[str] = None
    distribution_type_pz: Optional[str] = None
    sigma_x: Optional[float] = None
    sigma_px: Optional[float] = None
    sigma_y: Optional[float] = None
    sigma_py: Optional[float] = None
    sigma_z: Optional[float] = None
    sigma_pz: Optional[float] = None
    gaussian_cutoff_x: Optional[float] = None
    gaussian_cutoff_px: Optional[float] = None
    gaussian_cutoff_y: Optional[float] = None
    gaussian_cutoff_py: Optional[float] = None
    gaussian_cutoff_z: Optional[float] = None
    gaussian_cutoff_pz: Optional[float] = None
    plateau_bunch_length: Optional[float] = None
    plateau_rise_time: Optional[float] = None
    correlation_kinetic_energy: Optional[float] = None
    offset_x: Optional[float] = None
    normalized_horizontal_emittance: Optional[float] = None
    correlation_px: Optional[float] = None
    offset_y: Optional[float] = None
    normalized_vertical_emittance: Optional[float] = None
    correlation_py: Optional[float] = None
    thermal_emittance: Optional[float] = None


@strawberry.input
class PartialLatticeFilterInput:
    """Input filter for flexible lattice querying"""

    facility: Optional[str] = None
    set_initial_conditions: Optional[str] = None
    sections: Optional[List[SectionInput]] = None


@strawberry.type
class LatticeResult:
    """Result object for lattice queries"""

    uuid: str
    facility: str
    set_initial_conditions: str
    section_count: int


@strawberry.type
class FacilityInfo:
    """Facility information"""

    name: str
    lattice_count: int


@strawberry.type
class SectionInfo:
    """Section information"""

    name: str
    facility: Optional[str] = None
    count: int


@strawberry.type
class SigmaResult:
    """Result object for sigma queries"""

    x: float
    y: float
    t: float
    cp: float
    gamma: float
    uuid: str


@strawberry.type
class TwissResult:
    """Result object for Twiss parameter queries"""

    alpha_x: float
    beta_x: float
    alpha_y: float
    beta_y: float
    eta_x: float
    eta_xp: float
    eta_y: float
    eta_yp: float
    emit_x: float
    emit_y: float
    nemit_x: float
    nemit_y: float
    uuid: str


@strawberry.type
class BeamSummaryParameter:
    name: str
    label: str
    unit: Optional[str]
    values: List[float]


@strawberry.type
class BeamSummaryData:
    x_parameter: BeamSummaryParameter
    y_parameters: List[BeamSummaryParameter]


@strawberry.type
class BeamSummaryResult:
    uuid: str
    facility: str
    beam_summary_data: Optional[BeamSummaryData]


@strawberry.type
class Beam:
    """Beam particle coordinates at a screen"""

    x: List[float]
    y: List[float]
    z: List[float]
    cpx: List[float]
    cpy: List[float]
    cpz: List[float]


@strawberry.type
class Query:
    @strawberry.field
    def get_beam_summary(self, uuid: str) -> Optional[BeamSummaryResult]:
        """Get beam summary data for a twiss plot for a given lattice UUID"""
        from gql import resolvers

        return resolvers.get_beam_summary(uuid)

    @strawberry.field
    def get_run_uuids(self) -> List[str]:
        """Get all run UUIDs for the configured facility"""
        from gql import resolvers

        return resolvers.get_run_uuids()

    @strawberry.field
    def get_screen_names(self, uuid: str) -> List[str]:
        """Get all screen names for a lattice UUID"""
        from gql import resolvers

        return resolvers.get_screen_names(uuid)

    @strawberry.field
    def get_marker_names(self, uuid: str) -> List[str]:
        """Get all marker names for a lattice UUID"""
        from gql import resolvers

        return resolvers.get_marker_names(uuid)

    @strawberry.field
    def get_screen_beam(self, uuid: str, name: str) -> Beam:
        """Get beam data for a screen in a lattice UUID"""
        from gql import resolvers

        return resolvers.get_screen_beam(uuid, name)

    @strawberry.field
    def find_lattices(
        self,
        facility: str,
        set_initial_conditions: Optional[str] = None,
        magnet_filter: Optional[List[MagnetInput]] = None,
        cavity_filter: Optional[List[CavityInput]] = None,
        section_filter: Optional[List[SectionInput]] = None,
        generator_filter: Optional[GeneratorInput] = None,
    ) -> List[LatticeResult]:
        """
        Find lattices matching the provided filter criteria.
        All filter fields are optional - only provided fields will be used for matching.
        """
        from gql import resolvers

        return resolvers.find_lattices(
            facility,
            set_initial_conditions,
            magnet_filter,
            cavity_filter,
            section_filter,
            generator_filter,
        )

    @strawberry.field
    def get_facilities(self) -> List[FacilityInfo]:
        """Get all available facilities with lattice counts"""
        from gql import resolvers

        return resolvers.get_facilities()

    @strawberry.field
    def get_section_names(self, facility: Optional[str] = None) -> List[SectionInfo]:
        """Get all section names, optionally filtered by facility"""
        from gql import resolvers

        return resolvers.get_section_names(facility)

    @strawberry.field
    def get_lattice_by_uuid(self, uuid: str) -> Optional[LatticeResult]:
        """Get a specific lattice by UUID"""
        from gql import resolvers

        return resolvers.get_lattice_by_uuid(uuid)

    @strawberry.field
    def get_lattice_by_beam_sizes(
        self, beam_sizes: SigmaRangeInput
    ) -> List[SigmaResult]:
        """Get lattices matching the provided beam sizes (sigma values)"""
        from gql import resolvers

        return resolvers.get_lattice_by_beam_sizes_range(beam_sizes)

    @strawberry.field
    def get_lattice_by_twiss_parameters(
        self, twiss_params: TwissRangeInput
    ) -> List[TwissResult]:
        """Get lattices matching the provided Twiss parameters"""
        from gql import resolvers

        return resolvers.get_lattice_by_twiss_parameters_range(twiss_params)

    @strawberry.field
    def get_lattice_by_magnet_settings_range(
        self, magnet_settings: MagnetRangeInput
    ) -> List[LatticeResult]:
        """Get lattices matching the provided magnet settings"""
        from gql import resolvers

        return resolvers.get_lattice_by_magnet_settings_range(magnet_settings)

    @strawberry.field
    def get_lattice_by_cavity_settings_range(
        self, cavity_settings: CavityRangeInput
    ) -> List[LatticeResult]:
        """Get lattices matching the provided cavity settings"""
        from gql import resolvers

        return resolvers.get_lattice_by_cavity_settings_range(cavity_settings)


schema = strawberry.Schema(query=Query)
