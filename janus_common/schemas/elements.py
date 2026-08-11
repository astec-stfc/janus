from datetime import datetime
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator
)

from typing import List, Dict, Type, Optional, Literal, Any
from enum import Enum
from janus_common.utils.numeric import round_it
from janus_common.utils.constants import SIGFIG


########################################################################
#                              Data Classes                            #
########################################################################

class InitialConditions(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",  # Prevents additional fields from being added
        validate_by_name=True,
    )
    alpha_x: float = 0.0
    beta_x: float = 0.0
    alpha_y: float = 0.0
    beta_y: float = 0.0
    eta_x: float = 0.0
    eta_xp: float = 0.0
    eta_y: float = 0.0
    eta_yp: float = 0.0
    emit_x: float = Field(alias="ex", default=0.0)
    emit_y: float = Field(alias="ey", default=0.0)
    nemit_x: float = Field(alias="enx", default=0.0)
    nemit_y: float = Field(alias="eny", default=0.0)


class Twiss(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",  # Prevents additional fields from being added
        validate_by_name=True,
    )
    alpha_x: float = 0.0
    beta_x: float = 0.0
    alpha_y: float = 0.0
    beta_y: float = 0.0
    eta_x: float = 0.0
    eta_xp: float = 0.0
    eta_y: float = 0.0
    eta_yp: float = 0.0
    emit_x: float = Field(alias="ex", default=0.0)
    emit_y: float = Field(alias="ey", default=0.0)
    nemit_x: float = Field(alias="enx", default=0.0)
    nemit_y: float = Field(alias="eny", default=0.0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def get_field_names(cls, by_alias=False) -> list[str]:
        field_names = []
        for k, v in cls.model_fields.items():
            if by_alias and v.alias:
                field_names.append(v.alias)
            else:
                field_names.append(k)
        return field_names


class Sigma(BaseModel):
    x: float = 0.0  # Assume m
    y: float = 0.0  # Assume m
    t: float = 0.0  # Assume s
    cp: float = 0.0  # Assume eV
    gamma: float = 0.0

    class Config:
        from_attributes = True


class Centroid(BaseModel):
    x: float = 0.0  # Assume m
    y: float = 0.0  # Assume m
    t: float = 0.0  # Assume s
    cp: float = 0.0  # Assume eV
    gamma: float = 0.0
    q: float = 0  # Assume C

    class Config:
        from_attributes = True


class Covariance(BaseModel):
    xx: float = 0.0
    xxp: float = 0.0
    yy: float = 0.0
    yyp: float = 0.0
    xy: float = 0.0
    xyp: float = 0.0
    yxp: float = 0.0

    class Config:
        from_attributes = True


class Beam(BaseModel):
    x: List[float] | None = None
    y: List[float] | None = None
    z: List[float] | None = None
    cpx: List[float] | None = None
    cpy: List[float] | None = None
    cpz: List[float] | None = None

    class Config:
        from_attributes = True


class Intensity(BaseModel):
    min: float = 0.0  # Assume normalised [0,1]?
    max: float = 0.0  # Assume normalised [0,1]?
    mean: float = 0.0  # Assume normalised [0,1]?
    median: float = 0.0  # Assume normalised [0,1]?

    class Config:
        from_attributes = True


class CameraAnalysis(BaseModel):
    sigma: Sigma | None = None  # Assume pixels
    centroid: Centroid | None = None  # Assume pixels
    covariance: Covariance | None = None  # Assume pixels
    intensity: Intensity | None = None  # Assume normalised [0,1]?

    class Config:
        from_attributes = True


########################################################################
#                             Element Classes                          #
########################################################################

class Generator(BaseModel):

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    uuid: str | None = None
    enable: bool = False
    combine_distributions: bool = False
    number_of_particles: int
    species: Literal["electron", "proton", "positron", "hydrogen"]
    probe_particle: bool = True
    noise_reduction: bool = True
    cathode: bool
    charge: float
    # reference_position: float = 0.0
    initial_momentum: float = 0.0
    distribution_type_x: Literal["p", "plateau", "flattop", "g", "gaussian", "i", "r", "radial"] = "g"
    distribution_type_px: Literal["p", "plateau", "flattop", "g", "gaussian", "i", "r", "radial"] = "g"
    distribution_type_y: Literal["p", "plateau", "flattop", "g", "gaussian", "i", "r", "radial"] = "g"
    distribution_type_py: Literal["p", "plateau", "flattop", "g", "gaussian", "i", "r", "radial"] = "g"
    distribution_type_z: Literal["p", "plateau", "flattop", "g", "gaussian", "i", "r", "radial"] = "g"
    distribution_type_pz: Literal["p", "plateau", "flattop", "g", "gaussian", "i", "r", "radial"] = "g"
    sigma_x: float = Field(gt=0.0)
    sigma_px: float = Field(ge=0.0, default=0.0)
    sigma_y: float = Field(gt=0.0)
    sigma_py: float = Field(ge=0.0, default=0.0)
    sigma_z: float = Field(ge=0.0, default=0.0)
    sigma_pz: float = Field(ge=0.0, default=0.0)
    gaussian_cutoff_x: float = Field(gt=0.0, default=3.0)
    gaussian_cutoff_px: float = Field(gt=0.0, default=3.0)
    gaussian_cutoff_y: float = Field(gt=0.0, default=3.0)
    gaussian_cutoff_py: float = Field(gt=0.0, default=3.0)
    gaussian_cutoff_z: float = Field(gt=0.0, default=3.0)
    gaussian_cutoff_pz: float = Field(gt=0.0, default=3.0)
    plateau_bunch_length: float = Field(ge=0.0, default=0.0)
    plateau_rise_time: float = Field(ge=0.0, default=0.0)
    correlation_kinetic_energy: float = 0.0
    offset_x: float = 0.0
    normalized_horizontal_emittance: float = Field(ge=0.0, default=0.0)
    correlation_px: float = 0.0
    offset_y: float = 0.0
    normalized_vertical_emittance: float = Field(ge=0.0, default=0.0)
    correlation_py: float = 0.0
    thermal_emittance: float = Field(ge=0.0, default=0.0)

    @model_validator(mode="after")
    def validate_longitudinal_distribution(self):
        if self.distribution_type_z in {"p", "plateau", "flattop"}:
            if self.plateau_bunch_length <= 0.0:
                raise ValueError(
                    "plateau_bunch_length must be > 0 for flat-top longitudinal profiles"
                )
        if self.distribution_type_z in {"g", "gaussian", "i", "r", "radial"}:
            if self.sigma_z <= 0.0:
                raise ValueError(
                    "sigma_z must be > 0 for gaussian longitudinal profiles"
                )
        return self

    @staticmethod
    def get_elements() -> List:
        return []


class Element(BaseModel):
    name: str
    type: str
    length: float | int = 0.0
    subtype: str | None = None
    twiss: Twiss | None = None  # This should be None *from* EPICS
    sigma: Sigma | None = None  # This should be None *from* EPICS
    centroid: Centroid | None = None  # This should be None *from* EPICS
    updated: bool = False

    class Config:
        from_attributes = True

    @field_serializer("subtype", return_type=str)
    def serialise_subtype(self, subtype: Enum):
        if subtype is None:
            return subtype
        if isinstance(subtype, str):
            return subtype
        return subtype.name


class PhotonMonitor(Element):  # RESTFrame --> EPICS
    type: str = Field(default="PhotonMonitor", frozen=True)
    intensity: float = 0.0

    class Config:
        from_attributes = True


class BPM(Element):  # RESTFrame --> EPICS
    type: str = Field(default="BPM", frozen=True)

    class Config:
        from_attributes = True


class Camera(Element):  # RESTFrame --> EPICS
    type: str = Field(default="Camera", frozen=True)
    analysis: CameraAnalysis

    class Config:
        from_attributes = True


class PositionEnum(str, Enum):
    YAG = "YAG"
    VYAG = "VYAG"
    VSLIT = "VSlit"
    HSLIT = "HSlit"
    RF = "RF"
    VRF = "VRF"
    RETRACTED = "Retracted"

    class Config:
        from_attributes = True


class Marker(Element):  # RESTFrame --> EPICS
    type: str = Field(default="Marker", frozen=True)
    beam: Beam | None = None  # Beam at this marker

    class Config:
        from_attributes = True


class Screen(Element):  # RESTFrame --> EPICS
    type: str = Field(default="Screen", frozen=True)
    position: PositionEnum | None = PositionEnum("YAG")
    camera: Camera  # Associated Camera
    beam: Beam | None = None  # Beam at this marker

    class Config:
        from_attributes = True


class MagnetEnum(str, Enum):
    dipole = "dipole"
    quadrupole = "quadrupole"
    sextupole = "sextupole"
    corrector = "corrector"
    solenoid = "solenoid"
    wiggler = "wiggler"

    class Config:
        from_attributes = True


class Magnet(Element):  # RESTFrame <--> EPICS
    type: str = Field(default="Magnet", frozen=True)
    subtype: MagnetEnum
    KnL: list[float] | None = (
        None  # List in order of n (0=dipole, 1=quad, 2=sext, ...). Ideal
        # dipole = [K0L]; quad = [0, K1L] etc.
    )
    momentum: float = 0.0
    field_amplitude: float | None = None

    class Config:
        from_attributes = True
    
    @field_validator("KnL", mode="before")
    def validate_knl(cls, knl):
        if knl is None:
            return knl
        if not isinstance(knl, list):
            raise TypeError("KnL must be a list")
        return [round_it(float(k), SIGFIG) for k in knl]

    @field_validator("field_amplitude", mode="before")
    @classmethod
    def round_field_amplitude(cls, v):
        """Round field_amplitude to SIGFIG precision for consistency with DB storage."""
        if v is None:
            return v
        return round_it(float(v), SIGFIG)

    @field_serializer("KnL", return_type=list)
    def serialise_subtype(self, KnL: list[float] | None):
        if KnL is None:
            return KnL
        if isinstance(KnL, list):
            return [round_it(float(k), SIGFIG) for k in KnL]
        raise TypeError("KnL must be a list")

    @property
    def angle(self) -> float | None:
        if self.subtype == MagnetEnum.dipole and self.KnL is not None and len(self.KnL) > 0:
            return self.KnL[0]  # Assuming K0L for dipole
        return None

    @property
    def k1l(self) -> float | None:
        if self.subtype == MagnetEnum.quadrupole and self.KnL is not None and len(self.KnL) > 1:
            return self.KnL[1]  # Assuming K1L for quadrupole
        return None

    @property
    def k2l(self) -> float | None:
        if self.subtype == MagnetEnum.sextupole and self.KnL is not None and len(self.KnL) > 2:
            return self.KnL[2]  # Assuming K2L for sextupole
        return None

class CollimatorEnum(str, Enum):
    horizontal = "horizontal"
    vertical = "vertical"
    circular = "circular"
    elliptical = "elliptical"

    class Config:
        from_attributes = True


class Collimator(Element):  # RESTFrame <--> EPICS
    type: str = Field(default="Collimator", frozen=True)
    subtype: CollimatorEnum
    aperture: float | None = None  # Assume m
    position: float | None = None  # Assume m relative to middle of pipe?

    class Config:
        from_attributes = True


class CavityEnum(str, Enum):
    linac = "linac"
    harmonic = "harmonic"
    deflecting = "deflecting"
    wakefield = "wakefield"  # Laser Plasma, dielectric etc.

    class Config:
        from_attributes = True


class Cavity(Element):  # RESTFrame <-- EPICS
    type: str = Field(default="Cavity", frozen=True)
    subtype: CavityEnum
    crest: float | None = 0.0  # Assume degress
    phase: float = 0.0  # Assume degrees
    field_amplitude: float = 0.0  # Assume W
    gradient: float | None = 0.0  # Assume eV/m

    class Config:
        from_attributes = True

    @field_validator("crest", "phase", "field_amplitude", "gradient", mode="before")
    @classmethod
    def round_cavity_fields(cls, v):
        """Round cavity fields to SIGFIG precision for consistency with DB storage."""
        if v is None:
            return v
        return round_it(float(v), SIGFIG)


class Laser(Element):  # RESTFrame <-- EPICS
    type: str = Field(default="Laser", frozen=True)

    class Config:
        from_attributes = True

    # The following are not "obviously" implemented in EPICS,
    # but *are* changeable properties of the laser
    # - I think we can ignore them for now
    # t:            float | None = None  # Assume s
    # (sigma for "Gaussian", bunch length for "FlatTop")
    # xy_dist:        str | None = None  # "Gaussian" or "FlatTop"
    # t_dist:         str | None = None  # "Gaussian" or "FlatTop"
    # t_emit:       float | None = None
    # # Assume units of 1 (i.e. values ~ <1e-3)


class BeamSummary(BaseModel):
    alpha_x: List[float] | None = None
    beta_x: List[float] | None = None
    alpha_y: List[float] | None = None
    beta_y: List[float] | None = None
    energy: List[float] | None = None  # Assume eV
    charge: List[float] | None = None
    n_particles: List[float] | None = None  # Assume number of particles
    momentum: List[float] | None = None
    emittance_x: List[float] | None = None
    emittance_y: List[float] | None = None
    normalised_emittance_x: List[float] | None = None
    normalised_emittance_y: List[float] | None = None
    sigma_x: List[float] | None = None
    sigma_y: List[float] | None = None
    sigma_t: List[float] | None = None
    centroids_x: List[float] | None = None
    centroids_y: List[float] | None = None
    centroids_t: List[float] | None = None
    position: List[float] | None = None  # Also called s/z/timestep
    cov_xx: List[float] | None = None  # Covariance xx
    cov_xxp: List[float] | None = None  # Covariance xxp
    cov_yy: List[float] | None = None  # Covariance yy
    cov_yyp: List[float] | None = None  # Covariance yyp
    cov_xy: List[float] | None = None  # Covariance xy
    cov_xyp: List[float] | None = None  # Covariance xyp


class Section(BaseModel):
    name: str | None = None
    uuid: str | None = None
    model: str | None = None
    initial_conditions: InitialConditions | None = None
    screens: List[Screen] | None = None
    bpms: List[BPM] | None = None
    magnets: List[Magnet] | None = None
    cavities: List[Cavity] | None = None
    lasers: List[Laser] | None = None
    markers: List[Marker] | None = None
    photonmonitors: List[PhotonMonitor] | None = None
    beam_summary: BeamSummary | None = None

    class Config:
        from_attributes = True

    def get_elements(self) -> List[Element]:
        elems = []

        for typ in [
            self.screens,
            self.bpms,
            self.magnets,
            self.cavities,
            self.lasers,
            self.markers,
            self.photonmonitors,
        ]:
            if typ is not None:
                elems += typ
        return elems
    
    def get_element(self, name: str) -> Optional[Element]:
        for elem in self.get_elements():
            if elem.name == name:
                return elem
        return None

    def get_elements_dict(self) -> Dict:
        elems = {}
        for elem in self.get_elements():
            if elem.name not in elems:
                elems.update({elem.name: elem})
        return elems


class Lattice(BaseModel):
    generator: Generator | None = None
    facility: str | None = "CLARA"
    set_initial_conditions: str = ""
    sections: Dict[str, Section]
    uuid: str | None = None
    timestamp: datetime | None = None
    beam_summary: BeamSummary | None = None
    success: bool | None = None
    client_id: str | None = None

    class Config:
        from_attributes = True

    @field_validator("timestamp", mode="before")
    def validate_timestamp(cls, value):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value)
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return datetime.fromtimestamp(float(value))
        return value

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.isoformat()

    def get_elements(
        self,
        elem_type: Optional[Type[Element]] = None,
    ) -> List[Element]:
        elems = []
        for _, section in self.sections.items():
            for typ in [
                section.screens,
                section.bpms,
                section.magnets,
                section.cavities,
                section.lasers,
                section.markers,
                section.photonmonitors,
            ]:
                if typ is not None:
                    if elem_type is None:
                        elems += typ
                    else:
                        elems += [
                            elem
                            for elem in typ
                            if isinstance(
                                elem,
                                elem_type,
                            )
                        ]
        return elems

    def get_elements_dict(
        self,
        elem_type: Optional[Type[Element]] = None,
    ) -> Dict:
        elems = {}
        for elem in self.get_elements(elem_type):
            if elem.name not in elems:
                elems.update({elem.name: elem})
        return elems

    def get_sections(self) -> List[Section]:
        return [section for _, section in self.sections.items()]

    def without_large_float_arrays(self) -> "Lattice":
        """Return a deep-copied lattice with large beam arrays stripped to None."""
        lattice = self.model_copy(deep=True)

        if lattice.beam_summary is not None:
            for field_name in lattice.beam_summary.model_fields:
                setattr(lattice.beam_summary, field_name, None)

        for section in lattice.sections.values():
            if section.screens:
                for screen in section.screens:
                    if screen.beam is None:
                        continue
                    for field_name in screen.beam.model_fields:
                        setattr(screen.beam, field_name, None)

            if section.markers:
                for marker in section.markers:
                    if marker.beam is None:
                        continue
                    for field_name in marker.beam.model_fields:
                        setattr(marker.beam, field_name, None)

        return lattice

    def to_binary(self, compress: bool = True, compression_level: int = 3) -> bytes:
        """Serialize this lattice into the shared binary transport format.

        The binary form keeps the schema structure in JSON metadata while moving
        large float arrays into a contiguous binary payload for transport/storage.
        """
        from janus_common.schemas.binary_lattice_codec import lattice_to_binary

        return lattice_to_binary(self, compress=compress, compression_level=compression_level)

    def binary_metadata(self) -> Dict[str, Any]:
        """Build the binary metadata manifest without materializing payload bytes."""
        from janus_common.schemas.binary_lattice_codec import build_lattice_binary_metadata

        return build_lattice_binary_metadata(self)

    @classmethod
    def from_binary(
        cls,
        data: bytes,
        arrays_as_lists: bool = True,
    ) -> "Lattice":
        """Deserialize shared binary transport bytes back into a Lattice instance.

        ``arrays_as_lists=False`` is useful on hot paths that want numpy arrays
        during intermediate processing before Pydantic list materialization.
        """
        from janus_common.schemas.binary_lattice_codec import binary_to_lattice

        lattice_dict = binary_to_lattice(data, arrays_as_lists=arrays_as_lists)
        return cls.model_validate(lattice_dict)


class SimulationState(Enum):
    COMPLETE = 0
    TRACKING = 1
    ERROR = 2

class SimulationMode(Enum):
    AUTO = 0
    TRIGGER = 1

class SimulationTrigger(Enum):
    BYPASS = 0
    ACTIVATE = 1
