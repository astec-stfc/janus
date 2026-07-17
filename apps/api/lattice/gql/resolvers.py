"""GraphQL resolvers for lattice database queries"""

import os
from typing import Optional, List, Any, Dict, Tuple
from core.database import SessionLocal
from core.models import (
    Lattice as DBLattice,
    Section as DBSection,
    Element as DBElement,
    Magnets as DBMagnet,
    Cavities as DBCavity,
    Generator as DBGenerator,
    InitialConditions as DBInitialConditions,
)
from sqlalchemy import and_, func
from sqlalchemy.orm.attributes import InstrumentedAttribute
from gql.schemas import (
    BeamSummaryData,
    BeamSummaryParameter,
    BeamSummaryResult,
    CavityInput,
    Beam,
    GeneratorInput,
    LatticeResult,
    FacilityInfo,
    MagnetInput,
    SectionInfo,
    SectionInput,
    SigmaRangeInput,
    SigmaResult,
    TwissRangeInput,
    TwissResult,
    MagnetRangeInput,
    CavityRangeInput,
)
from core.utilities import convert_db_schema_to_lattice

FLOAT_TOLERANCE = 1e-4


def get_beam_summary(uuid: str) -> Optional[BeamSummaryResult]:
    """Get beam summary data for a Twiss plot for the given lattice UUID."""
    db = SessionLocal()
    try:
        db_lattice = (
            db.query(DBLattice).filter(DBLattice.uuid == uuid).one_or_none()
        )
        if not db_lattice:
            return None

        lattice = convert_db_schema_to_lattice(db_lattice)
        beam_summary = lattice.beam_summary

        if not beam_summary:
            return BeamSummaryResult(
                uuid=lattice.uuid,
                facility=lattice.facility or "",
                beam_summary_data=None,
            )

        y_parameters = [
            BeamSummaryParameter(name=field, label=field, unit=None, values=values)
            for field, values in beam_summary.model_dump().items()
            if field != "position" and isinstance(values, list) and len(values) > 0
        ]

        return BeamSummaryResult(
            uuid=lattice.uuid,
            facility=lattice.facility or "",
            beam_summary_data=BeamSummaryData(
                x_parameter=BeamSummaryParameter(
                    name="position",
                    label="Position",
                    unit="m",
                    values=beam_summary.position or [],
                ),
                y_parameters=y_parameters,
            ),
        )
    finally:
        db.close()


def get_run_uuids() -> List[str]:
    """Get all run UUIDs for the facility configured in env."""
    db = SessionLocal()
    try:
        return [
            row[0]
            for row in db.query(DBLattice.uuid)
            .filter(DBLattice.facility == os.getenv("FACILITY", "CLARA"))
            .all()
        ]
    finally:
        db.close()


def get_screen_names(uuid: str) -> List[str]:
    """Get all screen names for a lattice UUID."""
    db = SessionLocal()
    try:
        lattice = db.query(DBLattice).filter(DBLattice.uuid == uuid).one_or_none()
        if not lattice:
            raise ValueError(f"No lattice found with uuid: {uuid}")
        return [
            screen.name for section in lattice.sections for screen in section.screens
        ]
    finally:
        db.close()


def get_marker_names(uuid: str) -> List[str]:
    """Get all marker names for a lattice UUID."""
    db = SessionLocal()
    try:
        lattice = db.query(DBLattice).filter(DBLattice.uuid == uuid).one_or_none()
        if not lattice:
            raise ValueError(f"No lattice found with uuid: {uuid}")
        return [
            marker.name for section in lattice.sections for marker in section.markers
        ]
    finally:
        db.close()


def get_screen_beam(uuid: str, name: str) -> Beam:
    """Get beam data for a screen in a lattice UUID."""
    db = SessionLocal()
    try:
        lattice = db.query(DBLattice).filter(DBLattice.uuid == uuid).one_or_none()
        if not lattice:
            raise ValueError(f"No lattice found with uuid: {uuid}")
        for section in lattice.sections:
            for screen in section.screens:
                if screen.name == name:
                    if screen.beam is None:
                        raise ValueError(
                            f"No beam data for screen '{name}' in lattice uuid: {uuid}"
                        )
                    return Beam(
                        x=screen.beam.x,
                        y=screen.beam.y,
                        z=screen.beam.z,
                        cpx=screen.beam.cpx,
                        cpy=screen.beam.cpy,
                        cpz=screen.beam.cpz,
                    )
        raise ValueError(f"No screen '{name}' found for lattice uuid: {uuid}")
    finally:
        db.close()


def columns_within_tolerance(
    value1: InstrumentedAttribute,
    value2: InstrumentedAttribute,
    tolerance: float = FLOAT_TOLERANCE,
) -> float:
    """Check whether two values are within a set tolerance."""
    return func.abs(value1 - value2) <= tolerance


def check_range(value: Optional[float], value_range: Optional[List[float]]) -> bool:
    """
    Check if a value falls within a specified range.

    Args:
        value: The value to check (can be None)
        value_range: A list of [min, max] or None if no range check needed

    Returns:
        True if value is in range or no range specified, False otherwise
    """
    if value_range is None or value is None:
        return True
    if len(value_range) != 2:
        return False
    min_val, max_val = value_range
    return min_val <= value <= max_val


def check_attribute_ranges(
    obj: Any, attribute_ranges: Dict[str, Tuple[float, float]]
) -> bool:
    """
    Check if an object's attributes fall within specified ranges.

    Args:
        obj: The object to check attributes on
        attribute_ranges: Dict mapping attribute names to (min, max) tuples

    Returns:
        True if all attributes are in range, False if any are out of range

    Example:
        >>> ranges = {'alpha_x': (-1, 1), 'beta_x': (0, 10)}
        >>> check_attribute_ranges(twiss_obj, ranges)
    """
    for attr_name, (min_val, max_val) in attribute_ranges.items():
        if not hasattr(obj, attr_name):
            return False
        value = getattr(obj, attr_name)
        if value is None or not (min_val <= value <= max_val):
            return False
    return True


def filter_by_ranges(
    items: List[Any], range_spec: Dict[str, Optional[List[float]]]
) -> List[Any]:
    """
    Filter a list of items by multiple attribute ranges.

    Args:
        items: List of objects to filter
        range_spec: Dict mapping attribute names to [min, max] ranges (or None to skip)

    Returns:
        Filtered list containing only items matching all range criteria

    Example:
        >>> range_spec = {
        ...     'alpha_x': [-1, 1],
        ...     'beta_x': [0, 10],
        ...     'eta_x': None  # No range check for eta_x
        ... }
        >>> filtered = filter_by_ranges(elements, range_spec)
    """
    filtered = []
    for item in items:
        matches = True
        for attr_name, value_range in range_spec.items():
            if value_range is None:
                continue
            if not hasattr(item, attr_name):
                matches = False
                break
            value = getattr(item, attr_name)
            if value is None or not check_range(value, value_range):
                matches = False
                break
        if matches:
            filtered.append(item)
    return filtered


def _arrays_match_with_tolerance(
    db_array: List[float], input_array: List[float], tolerance: float = FLOAT_TOLERANCE
) -> bool:
    """
    Compare two arrays with floating-point tolerance.

    Args:
        db_array: Array from database
        input_array: Input array to compare
        tolerance: Maximum allowed difference per element (default 1e-6)

    Returns:
        True if arrays have same length and all elements match within tolerance
    """
    if db_array is None or input_array is None:
        return db_array == input_array

    if len(db_array) != len(input_array):
        return False

    return all(
        abs(db_val - input_val) < tolerance
        for db_val, input_val in zip(db_array, input_array)
    )


def find_lattices(
    facility: str,
    set_initial_conditions: Optional[str] = None,
    magnet_filter: List[MagnetInput] = None,
    cavity_filter: List[CavityInput] = None,
    section_filter: List[SectionInput] = None,
    generator_filter: GeneratorInput = None,
) -> List[LatticeResult]:
    """
    Find lattices matching the provided magnet and cavity filter criteria.
    Uses SQLAlchemy queries to efficiently find lattices containing matching magnets/cavities.

    Args:
        facility: Facility to search in (e.g., "CLARA")
        magnet_filter: List of MagnetInput filters - lattice must contain all matching magnets
        cavity_filter: List of CavityInput filters - lattice must contain all matching cavities

    Returns:
        List of LatticeResult objects that match all filter criteria
    """
    db = SessionLocal()
    try:
        # this will store uuids that match ALL filters
        combined_matching_uuids = None
        generator_uuids = None
        magnet_uuids = None
        cavity_uuids = None
        section_uuids = None
        # Process generator filter
        if generator_filter:
            conditions = [
                DBLattice.facility == facility,
                DBGenerator.enable == generator_filter.enable,
            ]
            if generator_filter.combine_distributions:
                conditions.append(
                    DBGenerator.combine_distributions
                    == generator_filter.combine_distributions
                )
            if generator_filter.number_of_particles:
                conditions.append(
                    DBGenerator.number_of_particles
                    == generator_filter.number_of_particles
                )
            if generator_filter.species:
                conditions.append(DBGenerator.species == generator_filter.species)
            if generator_filter.probe_particle:
                conditions.append(
                    DBGenerator.probe_particle == generator_filter.probe_particle
                )
            if generator_filter.noise_reduction:
                conditions.append(
                    DBGenerator.noise_reduction == generator_filter.noise_reduction
                )
            if generator_filter.cathode:
                conditions.append(DBGenerator.cathode == generator_filter.cathode)
            if generator_filter.charge:
                conditions.append(DBGenerator.charge == generator_filter.charge)
            if generator_filter.initial_momentum:
                conditions.append(
                    DBGenerator.initial_momentum == generator_filter.initial_momentum
                )
            if generator_filter.distribution_type_x:
                conditions.append(
                    DBGenerator.distribution_type_x
                    == generator_filter.distribution_type_x
                )
            if generator_filter.distribution_type_px:
                conditions.append(
                    DBGenerator.distribution_type_px
                    == generator_filter.distribution_type_px
                )
            if generator_filter.distribution_type_y:
                conditions.append(
                    DBGenerator.distribution_type_y
                    == generator_filter.distribution_type_y
                )
            if generator_filter.distribution_type_py:
                conditions.append(
                    DBGenerator.distribution_type_py
                    == generator_filter.distribution_type_py
                )
            if generator_filter.distribution_type_z:
                conditions.append(
                    DBGenerator.distribution_type_z
                    == generator_filter.distribution_type_z
                )
            if generator_filter.distribution_type_pz:
                conditions.append(
                    DBGenerator.distribution_type_pz
                    == generator_filter.distribution_type_pz
                )
            if generator_filter.sigma_x:
                conditions.append(DBGenerator.sigma_x == generator_filter.sigma_x)
            if generator_filter.sigma_px:
                conditions.append(DBGenerator.sigma_px == generator_filter.sigma_px)
            if generator_filter.sigma_y:
                conditions.append(DBGenerator.sigma_y == generator_filter.sigma_y)
            if generator_filter.sigma_py:
                conditions.append(DBGenerator.sigma_py == generator_filter.sigma_py)
            if generator_filter.sigma_z:
                conditions.append(DBGenerator.sigma_z == generator_filter.sigma_z)
            if generator_filter.sigma_pz:
                conditions.append(DBGenerator.sigma_pz == generator_filter.sigma_pz)
            if generator_filter.correlation_kinetic_energy:
                conditions.append(
                    DBGenerator.correlation_kinetic_energy
                    == generator_filter.correlation_kinetic_energy
                )
            if generator_filter.correlation_px:
                conditions.append(
                    DBGenerator.correlation_px == generator_filter.correlation_px
                )
            if generator_filter.correlation_py:
                conditions.append(
                    DBGenerator.correlation_py == generator_filter.correlation_py
                )
            if generator_filter.offset_x:
                conditions.append(DBGenerator.offset_x == generator_filter.offset_x)
            if generator_filter.offset_y:
                conditions.append(DBGenerator.offset_y == generator_filter.offset_y)
            if generator_filter.gaussian_cutoff_x:
                conditions.append(
                    DBGenerator.gaussian_cutoff_x == generator_filter.gaussian_cutoff_x
                )
            if generator_filter.gaussian_cutoff_px:
                conditions.append(
                    DBGenerator.gaussian_cutoff_px
                    == generator_filter.gaussian_cutoff_px
                )
            if generator_filter.gaussian_cutoff_y:
                conditions.append(
                    DBGenerator.gaussian_cutoff_y == generator_filter.gaussian_cutoff_y
                )
            if generator_filter.gaussian_cutoff_py:
                conditions.append(
                    DBGenerator.gaussian_cutoff_py
                    == generator_filter.gaussian_cutoff_py
                )
            if generator_filter.gaussian_cutoff_z:
                conditions.append(
                    DBGenerator.gaussian_cutoff_z == generator_filter.gaussian_cutoff_z
                )
            if generator_filter.gaussian_cutoff_pz:
                conditions.append(
                    DBGenerator.gaussian_cutoff_pz
                    == generator_filter.gaussian_cutoff_pz
                )
            if generator_filter.normalized_horizontal_emittance:
                conditions.append(
                    DBGenerator.normalized_horizontal_emittance
                    == generator_filter.normalized_horizontal_emittance
                )
            if generator_filter.normalized_vertical_emittance:
                conditions.append(
                    DBGenerator.normalized_vertical_emittance
                    == generator_filter.normalized_vertical_emittance
                )
            if generator_filter.thermal_emittance:
                conditions.append(
                    DBGenerator.thermal_emittance == generator_filter.thermal_emittance
                )
            if generator_filter.plateau_bunch_length:
                conditions.append(
                    DBGenerator.plateau_bunch_length
                    == generator_filter.plateau_bunch_length
                )
            if generator_filter.plateau_rise_time:
                conditions.append(
                    DBGenerator.plateau_rise_time == generator_filter.plateau_rise_time
                )
            generator_query = (
                db.query(DBLattice.uuid)
                .join(DBGenerator, DBLattice.id == DBGenerator.lattice_id)
                .filter(and_(*conditions))
                .distinct()
                .all()
            )
            generator_uuids = {uuid[0] for uuid in generator_query}
            combined_matching_uuids = generator_uuids
        # Process magnet filters
        if magnet_filter:
            # Check all settings for all magnets in filter
            for magnet_input in magnet_filter:
                conditions = [DBLattice.facility == facility]
                if combined_matching_uuids is not None:
                    # Only get rows that match current uuid matches
                    conditions.append(DBLattice.uuid.in_(combined_matching_uuids))
                if magnet_input.name:
                    conditions.append(DBMagnet.name == magnet_input.name)
                if magnet_input.type:
                    conditions.append(DBMagnet.type == magnet_input.type)
                if isinstance(magnet_input.field_amplitude, (int, float)):
                    conditions.append(
                        func.abs(DBMagnet.field_amplitude)
                        - abs(magnet_input.field_amplitude)
                        < FLOAT_TOLERANCE
                    )
                if magnet_input.momentum is not None:
                    conditions.append(DBMagnet.momentum == magnet_input.momentum)
                # Find rows that match all conditions for a single magnet
                magnets_query = (
                    db.query(DBLattice.uuid, DBMagnet.KnL)
                    .join(DBSection, DBLattice.id == DBSection.lattice_id)
                    .join(DBMagnet, DBSection.id == DBMagnet.section_id)
                    .filter(and_(*conditions))
                    .distinct()
                    .all()
                )
                filter_uuids = set()
                # Find rows that match K values (special case as it is an array..)
                if magnet_input.KnL is not None:
                    for uuid, knl in magnets_query:
                        if _arrays_match_with_tolerance(knl, magnet_input.KnL):
                            filter_uuids.add(uuid)
                else:
                    filter_uuids = {uuid for uuid, _ in magnets_query}

                # Check that uuid matches previously found uuids
                if magnet_uuids is None:
                    magnet_uuids = filter_uuids
                else:
                    magnet_uuids = magnet_uuids.intersection(filter_uuids)
            combined_matching_uuids = magnet_uuids
        # Process cavity filters
        if cavity_filter:
            # Check all settings for all cavities in filter
            for cavity_input in cavity_filter:
                conditions = [DBLattice.facility == facility]
                if combined_matching_uuids is not None:
                    # Only get rows that match current uuid matches
                    conditions.append(DBLattice.uuid.in_(combined_matching_uuids))
                if cavity_input.name:
                    conditions.append(DBCavity.name == cavity_input.name)
                if cavity_input.type:
                    conditions.append(DBCavity.type == cavity_input.type)
                if isinstance(cavity_input.field_amplitude, (int, float)):
                    conditions.append(
                        func.abs(
                            DBCavity.field_amplitude - cavity_input.field_amplitude
                        )
                        < FLOAT_TOLERANCE
                    )
                if isinstance(cavity_input.phase, (int, float)):
                    conditions.append(DBCavity.phase == cavity_input.phase)
                if cavity_input.crest is not None:
                    conditions.append(DBCavity.crest == cavity_input.crest)
                if cavity_input.gradient is not None:
                    conditions.append(DBCavity.gradient == cavity_input.gradient)
                # Find rows that match all conditions for a single cavity
                cavity_query = (
                    db.query(DBLattice.uuid)
                    .join(DBSection, DBLattice.id == DBSection.lattice_id)
                    .join(DBCavity, DBSection.id == DBCavity.section_id)
                    .filter(and_(*conditions))
                    .distinct()
                    .all()
                )
                filter_uuids = {uuid[0] for uuid in cavity_query}
                # Check that uuid matches previously found uuids
                if cavity_uuids is None:
                    cavity_uuids = filter_uuids
                else:
                    cavity_uuids = cavity_uuids.intersection(filter_uuids)
            combined_matching_uuids = cavity_uuids
        # Process section filters
        if section_filter:
            # Precompute once
            section_allowed_ic_names = (
                set(set_initial_conditions.split(","))
                if set_initial_conditions
                else set("")
            )

            for section_input in section_filter:
                # Base conditions (same as you had)
                conditions = [
                    DBLattice.facility == facility,
                    DBLattice.set_initial_conditions == set_initial_conditions,
                ]

                if combined_matching_uuids is not None:
                    conditions.append(DBLattice.uuid.in_(combined_matching_uuids))

                if section_input.name:
                    conditions.append(DBSection.name == section_input.name)

                if section_input.model:
                    conditions.append(DBSection.model == section_input.model)

                # --- Initial conditions filtering in SQL ---
                use_ic_filter = (
                    section_input.initial_conditions is not None
                    and section_input.name in section_allowed_ic_names
                )

                if use_ic_filter:
                    ic_in = section_input.initial_conditions

                    # Build per-field tolerance filters only for fields that are not None

                    if ic_in.beta_x is not None:
                        conditions.append(
                            columns_within_tolerance(
                                DBInitialConditions.beta_x,
                                ic_in.beta_x,
                                FLOAT_TOLERANCE,
                            )
                        )
                    if ic_in.beta_y is not None:
                        conditions.append(
                            columns_within_tolerance(
                                DBInitialConditions.beta_y,
                                ic_in.beta_y,
                                FLOAT_TOLERANCE,
                            )
                        )
                    if ic_in.alpha_x is not None:
                        conditions.append(
                            columns_within_tolerance(
                                DBInitialConditions.alpha_x,
                                ic_in.alpha_x,
                                FLOAT_TOLERANCE,
                            )
                        )
                    if ic_in.alpha_y is not None:
                        conditions.append(
                            columns_within_tolerance(
                                DBInitialConditions.alpha_y,
                                ic_in.alpha_y,
                                FLOAT_TOLERANCE,
                            )
                        )
                    if ic_in.nemit_x is not None:
                        conditions.append(
                            columns_within_tolerance(
                                DBInitialConditions.nemit_x,
                                ic_in.nemit_x,
                                FLOAT_TOLERANCE,
                            )
                        )
                    if ic_in.nemit_y is not None:
                        conditions.append(
                            columns_within_tolerance(
                                DBInitialConditions.nemit_y,
                                ic_in.nemit_y,
                                FLOAT_TOLERANCE,
                            )
                        )

                    # IMPORTANT:
                    # Your Python logic explicitly excludes rows where initial_conditions is None.
                    # Using an INNER JOIN to DBInitialConditions matches that behaviour.
                    q = (
                        db.query(DBLattice.uuid)
                        .join(DBSection, DBSection.lattice_id == DBLattice.id)
                        .join(
                            DBInitialConditions,
                            DBInitialConditions.section_id == DBSection.id,
                        )
                        .filter(and_(*conditions))
                    )

                    # distinct UUIDs that match this section+IC filter
                    filter_uuids = {uuid for (uuid,) in q.distinct().all()}

                else:
                    # No IC filter -> just use section/lattice conditions
                    q = (
                        db.query(DBLattice.uuid)
                        .join(DBSection, DBSection.lattice_id == DBLattice.id)
                        .filter(and_(*conditions))
                    )
                    filter_uuids = {uuid for (uuid,) in q.distinct().all()}
                # Check that uuid matches previously found uuids
                if section_uuids is None:
                    section_uuids = filter_uuids
                else:
                    section_uuids = section_uuids.intersection(filter_uuids)
            combined_matching_uuids = section_uuids

        if not (magnet_filter or cavity_filter or section_filter or generator_filter):
            # No filters provided, return all lattices for facility
            combined_matching_uuids = {
                uuid[0]
                for uuid in db.query(DBLattice.uuid)
                .filter(DBLattice.facility == facility)
                .all()
            }

        if combined_matching_uuids:
            db_lattices = (
                db.query(DBLattice)
                .filter(DBLattice.uuid.in_(combined_matching_uuids))
                .all()
            )
        else:
            print(
                "No prior matching run found for current EPICS settings; "
                "starting a new simulation."
            )
            db_lattices = []

        return [
            LatticeResult(
                uuid=db_lattice.uuid,
                facility=db_lattice.facility,
                set_initial_conditions=db_lattice.set_initial_conditions,
                section_count=len(db_lattice.sections),
            )
            for db_lattice in db_lattices
        ]

    except Exception as e:
        print(f"Error finding lattices: {e}")
        return []
    finally:
        db.close()


def get_facilities() -> List[FacilityInfo]:
    """Get all available facilities with lattice counts"""
    db = SessionLocal()
    try:
        facility_counts = (
            db.query(DBLattice.facility, func.count(DBLattice.id))
            .group_by(DBLattice.facility)
            .all()
        )

        results = [
            FacilityInfo(name=facility, lattice_count=count)
            for facility, count in facility_counts
        ]

        return (
            results
            if results
            else [FacilityInfo(name=os.getenv("FACILITY", "CLARA"), lattice_count=0)]
        )
    except Exception as e:
        print(f"Error querying facilities: {e}")
        return []
    finally:
        db.close()


def get_section_names(facility: Optional[str] = None) -> List[SectionInfo]:
    """Get all section names, optionally filtered by facility"""
    db = SessionLocal()
    try:
        if facility:
            section_counts = (
                db.query(DBSection.name, DBLattice.facility, func.count(DBSection.id))
                .join(DBLattice)
                .filter(DBLattice.facility == facility)
                .group_by(DBSection.name, DBLattice.facility)
                .all()
            )
        else:
            section_counts = (
                db.query(DBSection.name, DBLattice.facility, func.count(DBSection.id))
                .join(DBLattice)
                .group_by(DBSection.name, DBLattice.facility)
                .all()
            )

        results = [
            SectionInfo(name=name, facility=fac, count=count)
            for name, fac, count in section_counts
        ]

        return results
    except Exception as e:
        print(f"Error querying sections: {e}")
        return []
    finally:
        db.close()


def get_lattice_by_uuid(uuid: str) -> Optional[LatticeResult]:
    """Get a specific lattice by UUID"""
    db = SessionLocal()
    try:
        db_lattice = db.query(DBLattice).filter(DBLattice.uuid == uuid).one_or_none()

        if db_lattice:
            return LatticeResult(
                uuid=db_lattice.uuid,
                facility=db_lattice.facility,
                set_initial_conditions=db_lattice.set_initial_conditions,
                section_count=len(db_lattice.sections),
            )
        return None
    except Exception as e:
        print(f"Error querying lattice by UUID: {e}")
        return None
    finally:
        db.close()


def get_lattice_by_magnet_settings_range(
    magnet_settings: MagnetRangeInput,
) -> List[LatticeResult]:
    """Get lattices matching the provided magnet settings"""
    db = SessionLocal()
    # Build query with filters
    query = (
        db.query(DBElement).join(DBMagnet).filter(DBMagnet.name == magnet_settings.name)
    )

    # Add field_amplitude filter if provided
    if magnet_settings.field_amplitude is not None:
        query = query.filter(
            DBMagnet.field_amplitude == magnet_settings.field_amplitude
        )

    # Add momentum filter if provided
    if magnet_settings.momentum is not None:
        query = query.filter(DBMagnet.momentum == magnet_settings.momentum)

    db_elements = query.all()
    magnet_ranges = {
        "KnL": magnet_settings.k_range,
    }
    filtered_elements = filter_by_ranges(db_elements, magnet_ranges)
    # Execute query with all filters applied at database level

    results = []
    seen_lattices = set()
    for db_element in filtered_elements:
        try:
            if hasattr(db_element, "section") and hasattr(
                db_element.section, "lattice"
            ):
                lattice_uuid = db_element.section.lattice.uuid
                if lattice_uuid in seen_lattices:
                    continue
                seen_lattices.add(lattice_uuid)
                results.append(
                    LatticeResult(
                        uuid=db_element.section.lattice.uuid,
                        facility=db_element.lattice.facility,
                        set_initial_conditions=db_element.lattice.set_initial_conditions,
                        section_count=len(db_element.section.lattice.sections),
                    )
                )
        except Exception as e:
            print(f"Error processing lattice: {e}")
            continue
    return results


def get_lattice_by_cavity_settings_range(
    cavity_settings: CavityRangeInput,
) -> List[LatticeResult]:
    """Get lattices matching the provided cavity settings"""
    db = SessionLocal()
    try:
        # Query cavities by name only
        query = db.query(DBElement).filter(DBElement.name == cavity_settings.name)
        matching_elements = query.all()

        # Build range specification dict
        cavity_ranges = {
            "field_amplitude": cavity_settings.field_amplitude_range,
            "phase": cavity_settings.phase_range,
            "crest": cavity_settings.crest_range,
            "gradient": cavity_settings.gradient_range,
        }

        # Filter by ranges
        filtered_elements = filter_by_ranges(matching_elements, cavity_ranges)

        # Build results, avoiding duplicates
        results = []
        seen_lattices = set()

        for db_element in filtered_elements:
            try:
                if hasattr(db_element, "section") and hasattr(
                    db_element.section, "lattice"
                ):
                    lattice_uuid = db_element.section.lattice.uuid
                    if lattice_uuid not in seen_lattices:
                        seen_lattices.add(lattice_uuid)
                        results.append(
                            LatticeResult(
                                uuid=lattice_uuid,
                                facility=db_element.section.lattice.facility,
                                set_initial_conditions=db_element.section.lattice.set_initial_conditions,
                                section_count=len(db_element.section.lattice.sections),
                            )
                        )
            except Exception as e:
                print(f"Error processing element: {e}")
                continue

        return results
    except Exception as e:
        print(f"Error querying lattices by cavity settings: {e}")
        return []
    finally:
        db.close()


def get_lattice_by_twiss_parameters_range(
    twiss_parameters: TwissRangeInput,
) -> List[TwissResult]:
    """Get lattices matching the provided Twiss parameters"""
    db = SessionLocal()
    try:
        # Query elements by name only
        query = db.query(DBElement).filter(
            DBElement.name == twiss_parameters.element_name
        )
        matching_elements = query.all()

        results = []

        for db_element in matching_elements:
            try:
                if not hasattr(db_element, "twiss") or db_element.twiss is None:
                    continue

                # Build range specification for twiss attributes
                twiss_ranges = {
                    "alpha_x": twiss_parameters.alpha_x_range,
                    "beta_x": twiss_parameters.beta_x_range,
                    "alpha_y": twiss_parameters.alpha_y_range,
                    "beta_y": twiss_parameters.beta_y_range,
                    "eta_x": twiss_parameters.eta_x_range,
                    "eta_xp": twiss_parameters.eta_xp_range,
                    "eta_y": twiss_parameters.eta_y_range,
                    "eta_yp": twiss_parameters.eta_yp_range,
                    "emit_x": twiss_parameters.emit_x_range,
                    "emit_y": twiss_parameters.emit_y_range,
                    "nemit_x": twiss_parameters.nemit_x_range,
                    "nemit_y": twiss_parameters.nemit_y_range,
                }

                # Check if twiss object matches all ranges
                if check_attribute_ranges(
                    db_element.twiss,
                    {k: tuple(v) for k, v in twiss_ranges.items() if v is not None},
                ):
                    if hasattr(db_element, "section") and hasattr(
                        db_element.section, "lattice"
                    ):
                        twiss = db_element.twiss
                        results.append(
                            TwissResult(
                                alpha_x=twiss.alpha_x,
                                beta_x=twiss.beta_x,
                                alpha_y=twiss.alpha_y,
                                beta_y=twiss.beta_y,
                                eta_x=twiss.eta_x,
                                eta_xp=twiss.eta_xp,
                                eta_y=twiss.eta_y,
                                eta_yp=twiss.eta_yp,
                                emit_x=twiss.emit_x,
                                emit_y=twiss.emit_y,
                                nemit_x=twiss.nemit_x,
                                nemit_y=twiss.nemit_y,
                                uuid=db_element.section.lattice.uuid,
                            )
                        )
            except Exception as e:
                print(f"Error processing element: {e}")
                continue

        return results
    except Exception as e:
        print(f"Error querying lattices by twiss parameters: {e}")
        return []
    finally:
        db.close()


def get_lattice_by_beam_sizes_range(beam_sizes: SigmaRangeInput) -> List[SigmaResult]:
    """Get lattices matching the provided beam sizes (sigma values)"""
    db = SessionLocal()
    try:
        # Query elements by name only
        query = db.query(DBElement).filter(DBElement.name == beam_sizes.element_name)
        matching_elements = query.all()

        # Build range specification for sigma attributes
        sigma_ranges = {
            "x": beam_sizes.x_range,
            "y": beam_sizes.y_range,
            "t": beam_sizes.t_range,
            "cp": beam_sizes.cp_range,
            "gamma": beam_sizes.gamma_range,
        }

        results = []
        for db_element in matching_elements:
            try:
                if not hasattr(db_element, "sigma") or db_element.sigma is None:
                    continue

                # Check if sigma object matches all ranges
                if check_attribute_ranges(
                    db_element.sigma,
                    {k: tuple(v) for k, v in sigma_ranges.items() if v is not None},
                ):
                    if hasattr(db_element, "section") and hasattr(
                        db_element.section, "lattice"
                    ):
                        sigma = db_element.sigma
                        results.append(
                            SigmaResult(
                                x=sigma.x,
                                y=sigma.y,
                                t=sigma.t,
                                cp=sigma.cp,
                                gamma=sigma.gamma,
                                uuid=db_element.section.lattice.uuid,
                            )
                        )
            except Exception as e:
                print(f"Error processing element: {e}")
                continue

        return results
    except Exception as e:
        print(f"Error querying lattices by beam sizes: {e}")
        return []
    finally:
        db.close()
