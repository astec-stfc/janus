from sqlalchemy import String, ForeignKey, Float, Boolean, Integer
from sqlalchemy import and_  # noqa: F401
from sqlalchemy.orm import (
    declarative_base,
    relationship,
    Mapped,
    mapped_column,
    validates,
)
from typing import List
from sqlalchemy.dialects.postgresql import ARRAY

Base = declarative_base()


class InitialConditions(Base):
    __tablename__ = "initial_conditions"
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    section: Mapped["Section"] = relationship(
        back_populates="initial_conditions", cascade="all, delete"
    )
    section_id = mapped_column(
        ForeignKey("section.id", ondelete="CASCADE", onupdate="CASCADE")
    )
    alpha_x: Mapped[float] = mapped_column(Float, nullable=False)
    beta_x: Mapped[float] = mapped_column(Float, nullable=False)
    eta_x: Mapped[float] = mapped_column(Float, nullable=False)
    eta_xp: Mapped[float] = mapped_column(Float, nullable=False)
    emit_x: Mapped[float] = mapped_column(Float, nullable=False)
    nemit_x: Mapped[float] = mapped_column(Float, nullable=False)
    alpha_y: Mapped[float] = mapped_column(Float, nullable=False)
    beta_y: Mapped[float] = mapped_column(Float, nullable=False)
    eta_y: Mapped[float] = mapped_column(Float, nullable=False)
    eta_yp: Mapped[float] = mapped_column(Float, nullable=False)
    emit_y: Mapped[float] = mapped_column(Float, nullable=False)
    nemit_y: Mapped[float] = mapped_column(Float, nullable=False)


class Twiss(Base):
    __tablename__ = "twiss"
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    element: Mapped["Element"] = relationship(
        back_populates="twiss", cascade="all, delete"
    )
    alpha_x: Mapped[float] = mapped_column(Float, nullable=False)
    beta_x: Mapped[float] = mapped_column(Float, nullable=False)
    eta_x: Mapped[float] = mapped_column(Float, nullable=False)
    eta_xp: Mapped[float] = mapped_column(Float, nullable=False)
    emit_x: Mapped[float] = mapped_column(Float, nullable=False)
    nemit_x: Mapped[float] = mapped_column(Float, nullable=False)
    alpha_y: Mapped[float] = mapped_column(Float, nullable=False)
    beta_y: Mapped[float] = mapped_column(Float, nullable=False)
    eta_y: Mapped[float] = mapped_column(Float, nullable=False)
    eta_yp: Mapped[float] = mapped_column(Float, nullable=False)
    emit_y: Mapped[float] = mapped_column(Float, nullable=False)
    nemit_y: Mapped[float] = mapped_column(Float, nullable=False)


class Sigma(Base):
    __tablename__ = "sigma"
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    element: Mapped["Element"] = relationship(
        back_populates="sigma", cascade="all, delete"
    )
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)
    t: Mapped[float] = mapped_column(Float, nullable=False)
    cp: Mapped[float] = mapped_column(Float, nullable=False)
    gamma: Mapped[float] = mapped_column(Float, nullable=False)


class Centroid(Base):
    __tablename__ = "centroid"
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    element: Mapped["Element"] = relationship(
        back_populates="centroid", cascade="all, delete"
    )
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)
    t: Mapped[float] = mapped_column(Float, nullable=False)
    cp: Mapped[float] = mapped_column(Float, nullable=False)
    gamma: Mapped[float] = mapped_column(Float, nullable=False)
    q: Mapped[float] = mapped_column(Float, nullable=False)


class Covariance(Base):
    __tablename__ = "covariance"
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    analysis: Mapped["CameraAnalysis"] = relationship(
        back_populates="covariance", cascade="all, delete"
    )
    xx: Mapped[float] = mapped_column(Float, nullable=False)
    xxp: Mapped[float] = mapped_column(Float, nullable=False)
    yy: Mapped[float] = mapped_column(Float, nullable=False)
    yyp: Mapped[float] = mapped_column(Float, nullable=False)
    xy: Mapped[float] = mapped_column(Float, nullable=False)
    xyp: Mapped[float] = mapped_column(Float, nullable=False)
    yxp: Mapped[float] = mapped_column(Float, nullable=False)


class Beam(Base):
    __tablename__ = "beam"
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    marker: Mapped["Markers"] = relationship(
        back_populates="beam", cascade="all, delete"
    )
    x: Mapped[list[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True), nullable=False
    )
    y: Mapped[list[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True), nullable=False
    )
    z: Mapped[list[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True), nullable=False
    )
    cpx: Mapped[list[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True), nullable=False
    )
    cpy: Mapped[list[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True), nullable=False
    )
    cpz: Mapped[list[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True), nullable=False
    )


class Intensity(Base):
    __tablename__ = "intensity"
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    analysis: Mapped["CameraAnalysis"] = relationship(
        back_populates="intensity", cascade="all, delete"
    )
    min: Mapped[float] = mapped_column(Float, nullable=False)
    max: Mapped[float] = mapped_column(Float, nullable=False)
    mean: Mapped[float] = mapped_column(Float, nullable=False)
    median: Mapped[float] = mapped_column(Float, nullable=False)


class CameraAnalysis(Base):
    __tablename__ = "camera_analysis"
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    camera: Mapped["Cameras"] = relationship(back_populates="analysis")
    covariance_id = mapped_column(
        ForeignKey("covariance.id", ondelete="CASCADE", onupdate="CASCADE")
    )
    covariance: Mapped["Covariance"] = relationship(
        foreign_keys=[covariance_id], back_populates="analysis"
    )
    intensity_id = mapped_column(
        ForeignKey("intensity.id", ondelete="CASCADE", onupdate="CASCADE")
    )
    intensity: Mapped["Intensity"] = relationship(
        foreign_keys=[intensity_id], back_populates="analysis"
    )


class Element(Base):
    __tablename__ = "elements"
    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), unique=False, nullable=False)
    type: Mapped[str] = mapped_column(String(50), unique=False, nullable=False)
    subtype: Mapped[str] = mapped_column(String(50), unique=False, nullable=True)

    # parent relationships
    # Should NEVER have `cascade="all, delete"` in `relationship`,
    # otherwise deleting this model deletes parent models.
    # machine_area: Mapped["MachineAreas"] = relationship(
    #     foreign_keys=[machine_area_id], back_populates="elements"
    # )
    twiss_id = mapped_column(
        ForeignKey("twiss.id", ondelete="CASCADE", onupdate="CASCADE")
    )
    twiss: Mapped["Twiss"] = relationship(
        foreign_keys=[twiss_id], back_populates="element"
    )
    sigma_id = mapped_column(
        ForeignKey("sigma.id", ondelete="CASCADE", onupdate="CASCADE")
    )
    sigma: Mapped["Sigma"] = relationship(
        foreign_keys=[sigma_id], back_populates="element"
    )

    centroid_id = mapped_column(
        ForeignKey("centroid.id", ondelete="CASCADE", onupdate="CASCADE")
    )
    centroid: Mapped["Centroid"] = relationship(
        foreign_keys=[centroid_id], back_populates="element"
    )
    updated: Mapped[bool] = mapped_column(
        Boolean, unique=False, nullable=False, default=False
    )
    __mapper_args__ = {"polymorphic_on": type}


class Cameras(Element):
    __tablename__ = "cameras"
    id: Mapped[int] = mapped_column(
        ForeignKey("elements.id"), primary_key=True, nullable=False
    )
    # arraydata: Mapped[str] = mapped_column(String(), nullable=False)
    analysis_id = mapped_column(
        ForeignKey("camera_analysis.id", ondelete="CASCADE", onupdate="CASCADE")
    )
    analysis: Mapped["CameraAnalysis"] = relationship(
        foreign_keys=[analysis_id], back_populates="camera"
    )
    __mapper_args__ = {"polymorphic_identity": "Camera"}


class Markers(Element):
    __tablename__ = "markers"
    id: Mapped[int] = mapped_column(
        ForeignKey("elements.id"), primary_key=True, nullable=False
    )
    section_id = mapped_column(
        ForeignKey("section.id", ondelete="CASCADE", onupdate="CASCADE")
    )
    section: Mapped["Section"] = relationship(
        foreign_keys=[section_id],
        back_populates="markers",
    )
    beam_id = mapped_column(
        ForeignKey(
            "beam.id",
            ondelete="CASCADE",
            onupdate="CASCADE",
        )
    )
    beam: Mapped["Beam"] = relationship(back_populates="marker", cascade="all, delete")
    __mapper_args__ = {"polymorphic_identity": "Marker"}


class Screens(Markers):
    __tablename__ = "screens"
    id: Mapped[int] = mapped_column(
        ForeignKey("markers.id"), primary_key=True, nullable=False
    )
    position: Mapped[str] = mapped_column(String(20), nullable=False, default="YAG")
    camera_id = mapped_column(
        ForeignKey("cameras.id", ondelete="CASCADE", onupdate="CASCADE"),
        unique=True,
    )
    camera: Mapped["Cameras"] = relationship(foreign_keys=[camera_id])
    __mapper_args__ = {"polymorphic_identity": "Screen"}


class Magnets(Element):
    __tablename__ = "magnets"
    id: Mapped[int] = mapped_column(
        ForeignKey("elements.id"), primary_key=True, nullable=False
    )
    section_id = mapped_column(
        ForeignKey("section.id", ondelete="CASCADE", onupdate="CASCADE")
    )
    section: Mapped["Section"] = relationship(
        foreign_keys=[section_id],
        back_populates="magnets",
    )
    KnL: Mapped[List[float]] = mapped_column(
        ARRAY(
            Float,
            zero_indexes=True,
        ),
        nullable=False,
    )
    gradient: Mapped[Float] = mapped_column(Float, nullable=True, default=0.0)
    field_amplitude: Mapped[Float] = mapped_column(Float, nullable=True, default=0.0)
    momentum: Mapped[float] = mapped_column(Float, nullable=False)
    __mapper_args__ = {"polymorphic_identity": "Magnet"}


class BPMs(Element):
    __tablename__ = "bpms"
    id: Mapped[int] = mapped_column(
        ForeignKey("elements.id"), primary_key=True, nullable=False
    )
    section_id = mapped_column(
        ForeignKey("section.id", ondelete="CASCADE", onupdate="CASCADE")
    )
    section: Mapped["Section"] = relationship(
        foreign_keys=[section_id],
        back_populates="bpms",
    )
    __mapper_args__ = {"polymorphic_identity": "BPM"}


class Lasers(Element):
    __tablename__ = "lasers"
    id: Mapped[int] = mapped_column(
        ForeignKey("elements.id"), primary_key=True, nullable=False
    )
    section_id = mapped_column(
        ForeignKey("section.id", ondelete="CASCADE", onupdate="CASCADE")
    )
    section: Mapped["Section"] = relationship(
        foreign_keys=[section_id],
        back_populates="lasers",
    )
    __mapper_args__ = {"polymorphic_identity": "Laser"}


class Cavities(Element):
    __tablename__ = "cavities"
    id: Mapped[int] = mapped_column(
        ForeignKey("elements.id"),
        primary_key=True,
        nullable=False,
    )
    section_id = mapped_column(
        ForeignKey("section.id", ondelete="CASCADE", onupdate="CASCADE")
    )
    section: Mapped["Section"] = relationship(
        foreign_keys=[section_id],
        back_populates="cavities",
    )
    crest: Mapped[Float] = mapped_column(Float, default=0.0)
    phase: Mapped[Float] = mapped_column(Float, nullable=False)
    field_amplitude: Mapped[Float] = mapped_column(Float, nullable=False)
    gradient: Mapped[Float] = mapped_column(Float, default=0.0)

    __mapper_args__ = {"polymorphic_identity": "Cavity"}


class BeamSummary(Base):
    __tablename__ = "beam_summary"
    id: Mapped[int] = mapped_column(
        primary_key=True, nullable=False, autoincrement=True
    )
    lattice_id = mapped_column(
        ForeignKey("lattices.id", ondelete="CASCADE", onupdate="CASCADE")
    )
    lattice: Mapped["Lattice"] = relationship(
        foreign_keys=[lattice_id],
        back_populates="beam_summary",
    )
    alpha_x: Mapped[List[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True),
        nullable=True,
    )
    beta_x: Mapped[List[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True),
        nullable=True,
    )
    alpha_y: Mapped[List[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True),
        nullable=True,
    )
    beta_y: Mapped[List[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True),
        nullable=True,
    )
    energy: Mapped[List[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True),
        nullable=True,
    )  # Assume eV
    charge: Mapped[List[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True),
        nullable=True,
    )
    n_particles: Mapped[List[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True),
        nullable=True,
    )  # Assume number of particles
    momentum: Mapped[List[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True),
        nullable=True,
    )
    emittance_x: Mapped[List[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True),
        nullable=True,
    )
    emittance_y: Mapped[List[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True),
        nullable=True,
    )
    normalised_emittance_x: Mapped[List[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True),
        nullable=True,
    )
    normalised_emittance_y: Mapped[List[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True),
        nullable=True,
    )
    sigma_x: Mapped[List[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True),
        nullable=True,
    )
    sigma_y: Mapped[List[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True),
        nullable=True,
    )
    centroids_x: Mapped[List[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True),
        nullable=True,
    )
    centroids_y: Mapped[List[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True),
        nullable=True,
    )
    position: Mapped[List[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True),
        nullable=True,
    )  # Also called s/z/timestep
    cov_xx: Mapped[List[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True),
        nullable=True,
    )
    cov_xxp: Mapped[List[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True),
        nullable=True,
    )
    cov_yy: Mapped[List[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True),
        nullable=True,
    )
    cov_yyp: Mapped[List[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True),
        nullable=True,
    )
    cov_xy: Mapped[List[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True),
        nullable=True,
    )
    cov_xyp: Mapped[List[float]] = mapped_column(
        ARRAY(Float, zero_indexes=True),
        nullable=True,
    )


class Generator(Base):
    __tablename__ = "generator"
    id: Mapped[int] = mapped_column(
        primary_key=True, nullable=False, autoincrement=True
    )
    lattice_id = mapped_column(
        ForeignKey("lattices.id", ondelete="CASCADE", onupdate="CASCADE")
    )
    lattice: Mapped["Lattice"] = relationship(
        foreign_keys=[lattice_id],
        back_populates="generator",
    )
    enable: Mapped[bool] = mapped_column(Boolean, nullable=True)
    combine_distributions: Mapped[bool] = mapped_column(Boolean, nullable=True)
    number_of_particles: Mapped[int] = mapped_column(Integer, nullable=True)
    species: Mapped[str] = mapped_column(String(50), nullable=True)
    probe_particle: Mapped[bool] = mapped_column(Boolean, nullable=True)
    noise_reduction: Mapped[bool] = mapped_column(Boolean, nullable=True)
    cathode: Mapped[bool] = mapped_column(Boolean, nullable=True)
    charge: Mapped[float] = mapped_column(Float, nullable=True)
    # reference_position: Mapped[List[float]] = mapped_column(
    #     ARRAY(Float, zero_indexes=True),
    #     nullable=True,
    # )
    initial_momentum: Mapped[float] = mapped_column(Float, nullable=True)
    distribution_type_x: Mapped[str] = mapped_column(String(50), nullable=True)
    distribution_type_px: Mapped[str] = mapped_column(String(50), nullable=True)
    distribution_type_y: Mapped[str] = mapped_column(String(50), nullable=True)
    distribution_type_py: Mapped[str] = mapped_column(String(50), nullable=True)
    distribution_type_z: Mapped[str] = mapped_column(String(50), nullable=True)
    distribution_type_pz: Mapped[str] = mapped_column(String(50), nullable=True)
    sigma_x: Mapped[float] = mapped_column(Float, nullable=True)
    sigma_px: Mapped[float] = mapped_column(Float, nullable=True)
    sigma_y: Mapped[float] = mapped_column(Float, nullable=True)
    sigma_py: Mapped[float] = mapped_column(Float, nullable=True)
    sigma_z: Mapped[float] = mapped_column(Float, nullable=True)
    sigma_pz: Mapped[float] = mapped_column(Float, nullable=True)
    correlation_kinetic_energy: Mapped[float] = mapped_column(Float, nullable=True)
    correlation_px: Mapped[float] = mapped_column(Float, nullable=True)
    correlation_py: Mapped[float] = mapped_column(Float, nullable=True)
    offset_x: Mapped[float] = mapped_column(Float, nullable=True)
    offset_y: Mapped[float] = mapped_column(Float, nullable=True)
    gaussian_cutoff_x: Mapped[float] = mapped_column(Float, nullable=True)
    gaussian_cutoff_px: Mapped[float] = mapped_column(Float, nullable=True)
    gaussian_cutoff_y: Mapped[float] = mapped_column(Float, nullable=True)
    gaussian_cutoff_py: Mapped[float] = mapped_column(Float, nullable=True)
    gaussian_cutoff_z: Mapped[float] = mapped_column(Float, nullable=True)
    gaussian_cutoff_pz: Mapped[float] = mapped_column(Float, nullable=True)
    normalized_horizontal_emittance: Mapped[float] = mapped_column(Float, nullable=True)
    normalized_vertical_emittance: Mapped[float] = mapped_column(Float, nullable=True)
    thermal_emittance: Mapped[float] = mapped_column(Float, nullable=True)
    plateau_bunch_length: Mapped[float] = mapped_column(Float, nullable=True)
    plateau_rise_time: Mapped[float] = mapped_column(Float, nullable=True)


class Section(Base):
    __tablename__ = "section"
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    uuid: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    lattice_id = mapped_column(
        ForeignKey("lattices.id", ondelete="CASCADE", onupdate="CASCADE")
    )
    lattice: Mapped["Lattice"] = relationship(
        foreign_keys=[lattice_id],
        back_populates="sections",
    )
    name: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )
    model: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # Model name for the section, e.g. ASTRA, elegant, etc.
    initial_conditions: Mapped[InitialConditions] = relationship(
        back_populates="section",
        cascade="all, delete",
    )
    screens: Mapped[List[Screens]] = relationship(
        back_populates="section", cascade="all, delete", overlaps="markers"
    )
    markers: Mapped[List[Markers]] = relationship(
        back_populates="section",
        cascade="all, delete",
        overlaps="screens",
        primaryjoin="and_(Section.id==Markers.section_id, Markers.type=='Marker')",
        viewonly=True,  # <-- Add this
    )
    bpms: Mapped[List[BPMs]] = relationship(
        back_populates="section",
        cascade="all, delete",
    )
    cavities: Mapped[List[Cavities]] = relationship(
        back_populates="section",
        cascade="all, delete",
    )
    magnets: Mapped[List[Magnets]] = relationship(
        back_populates="section",
        cascade="all, delete",
    )
    lasers: Mapped[List[Lasers]] = relationship(
        back_populates="section",
        cascade="all, delete",
    )

    @validates("screens")
    def validate_screens(self, _, value) -> Screens:
        return value

    @validates("bpms")
    def validate_bpms(self, _, value) -> BPMs:
        return value

    @validates("cavities")
    def validate_cavities(self, _, value) -> Cavities:
        return value

    @validates("magnets")
    def validate_magnets(self, _, value) -> Magnets:
        return value

    @validates("cameras")
    def validate_cameras(self, _, value) -> Cameras:
        return value

    @validates("lasers")
    def validate_lasers(self, _, value) -> Lasers:
        return value

    @validates("markers")
    def validate_markers(self, _, value) -> Markers:
        return value


class Lattice(Base):
    __tablename__ = "lattices"
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    uuid: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    facility: Mapped[str] = mapped_column(String(10), nullable=False)
    success: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )  # Whether the lattice ran successfully
    sections: Mapped[List["Section"]] = relationship(
        back_populates="lattice",
        cascade="all, delete",
    )
    beam_summary: Mapped[BeamSummary] = relationship(
        back_populates="lattice", cascade="all, delete"
    )
    generator: Mapped[Generator] = relationship(
        back_populates="lattice", cascade="all, delete"
    )
    set_initial_conditions: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
