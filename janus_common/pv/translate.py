"""Translate lattice and simulation schema data into process variable metadata.

This module provides helper classes and translators that generate structured
PV metadata from pydantic schema classes. It includes logic for type coercion,
name normalization, schema traversal, and creation of PV names for lattice
and simulation model fields.
"""

import re
from enum import Enum
from functools import cached_property
from math import floor, log10
from types import UnionType
from typing import (
    Any,
    Dict,
    List,
    Tuple,
    Type,
    Union,
    Literal,
    get_args,
    get_origin,
)
from pydantic import BaseModel, ValidationError
from janus_common.schemas.elements import (
    Element,
    Section,
    BeamSummary,
    Generator,
    InitialConditions,
    SimulationMode,
    SimulationState,
    SimulationTrigger,
)
from janus_common.utils.numeric import round_it
from janus_common.utils.constants import SIGFIG

SIM_PREFIX = "SIM"
VM_PREFIX = "VM"


class PVMetadata:
    """Base metadata container for a process variable.

    Attributes
    ----------
    name : str
        The PV name string.
    type : Type
        The expected Python type for the PV value.
    """

    name: str
    type: Type

    def __init__(self, name, type, *args, **kwargs):
        self.name = name
        self.type = type


class PVSchemaMetadata(PVMetadata):
    """Schema-aware PV metadata that can resolve values from a model.

    This class extends :class:`PVMetadata` with a path into a pydantic model.
    It can extract values from nested schema objects and coerce them to the
    correct PV type.
    """

    schema_attribute_path: Tuple[str]

    def __init__(self, name, type, schema_attribute_path, *args, **kwargs):
        super().__init__(name, type)
        self.schema_attribute_path = schema_attribute_path

    def get_schema_value(self, obj: Any) -> Any:
        """Retrieve a value from the target object using the schema path.

        Parameters
        ----------
        obj : Any
            The object from which to resolve the schema attribute path.

        Returns
        -------
        Any
            The resolved attribute value, or ``None`` if any path segment is
            missing.
        """
        try:
            for part in self.schema_attribute_path:
                obj = getattr(obj, part)
            if self.type is float and not isinstance(obj, bool):
                obj = round_it(obj, SIGFIG)
            return obj
        except AttributeError:
            return None

    def _nested_model_type(self, parent: Any, attr_name: str):
        if not isinstance(parent, BaseModel):
            return None
        field = parent.__pydantic_fields__.get(attr_name)
        if field is None:
            return None
        annotation = field.annotation
        origin = get_origin(annotation)
        if origin is Union or origin is UnionType:
            for arg in get_args(annotation):
                if isinstance(arg, type) and issubclass(arg, BaseModel):
                    return arg
            return None
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return annotation
        return None

    def set_schema_value(self, obj: Any, value: Any) -> None:
        """Set a schema value on a nested model object.

        Parameters
        ----------
        obj : Any
            The root object from which the schema path resolution begins.
        value : Any
            The value to assign to the last attribute in the schema path.
        """
        parent = obj
        for part in self.path[:-1]:
            next_parent = getattr(parent, part, None)
            if next_parent is None:
                model_type = self._nested_model_type(parent, part)
                if model_type is not None:
                    next_parent = model_type()
                    setattr(parent, part, next_parent)
            if next_parent is None:
                raise AttributeError(
                    f"No attribute found for path {self.schema_attribute_path}"
                )
            parent = next_parent
        if self.type is bool and isinstance(value, int):
            value = bool(value)
        elif self.type is int and not isinstance(value, bool):
            value = int(value)
        elif self.type is float and not isinstance(value, bool):
            value = round_it(float(value), SIGFIG)
        elif self.type is str and not isinstance(value, str):
            value = str(value)
        try:
            setattr(parent, self.path[-1], value)
        except ValidationError as e:
            raise ValueError(
                f"Failed to set value for {self.name} at path {self.schema_attribute_path}: {e}"
            ) from e
        except AttributeError as e:
            raise AttributeError(
                f"Failed to set value for {self.name} at path {self.schema_attribute_path}: {e}"
            ) from e

    def value_as_type(self, value: Any) -> Any:
        """Coerce a raw value to the metadata type expected by this PV.

        Parameters
        ----------
        value : Any
            The raw input value to convert.

        Returns
        -------
        Any
            The value converted to the type defined by ``self.type``.
        """
        if self.type is bool and isinstance(value, int):
            return bool(value)
        elif self.type is int and not isinstance(value, bool):
            return int(value)
        elif self.type is float and not isinstance(value, bool):
            return round_it(float(value), SIGFIG)
        elif self.type is str and not isinstance(value, str):
            return str(value)
        elif self.type is list and not isinstance(value, list):
            return [value]
        elif self.type is tuple and not isinstance(value, tuple):
            return (value,)
        return value

    @cached_property
    def path(self) -> Tuple[str]:
        return self.schema_attribute_path


class PVTranslator:
    """Base class for translating schema models into PV metadata.

    Subclasses build PV names and metadata from pydantic models and schema
    annotations. This base class provides shared type resolution and name
    normalization helpers.
    """

    def __init__(self, *args, **kwargs):
        pass

    def _normalize_class_name(self, cls_name: str) -> str:
        """Convert a CamelCase class name into uppercased hyphen-separated text.

        Parameters
        ----------
        cls_name : str
            The class name to normalize.

        Returns
        -------
        str
            The normalized class name, e.g. ``BeamSummary`` -> ``BEAM-SUMMARY``.
        """
        normalized = cls_name.replace("_", " ")
        normalized = re.sub(r"(.)([A-Z][a-z]+)", r"\1 \2", normalized)
        normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", normalized)
        return normalized.replace(" ", "-").upper()

    def _resolve_single_type(self, annotation):
        """Resolve a pydantic field annotation to a single Python type.

        The method handles ``Literal`` and ``Union`` annotations, as well as
        enum subclasses and PEP 604 union syntax.

        Parameters
        ----------
        annotation : Any
            The field annotation to resolve.

        Returns
        -------
        Type | None
            The resolved Python type for PV metadata.
        """
        origin = get_origin(annotation)
        # Handle Literal[...] types
        if origin is Literal:
            literal_args = get_args(annotation)
            if not literal_args:
                return str
            literal_types = {type(item) for item in literal_args}
            if len(literal_types) == 1:
                return next(iter(literal_types))
            if bool in literal_types and int in literal_types:
                # bool is a subclass of int, but Literal[True, False] should be bool
                return bool
            # Fallback for mixed values or unsupported literal content
            return str

        # Handle Union[...] types and | (PEP 604)
        if origin is Union or origin is UnionType:
            types = [t for t in get_args(annotation) if t is not type(None)]
            for t in types:
                t_origin = get_origin(t)
                if isinstance(t, type) and issubclass(t, Enum):
                    return str
                if t_origin is Literal:
                    literal_args = get_args(t)
                    if literal_args:
                        literal_types = {type(item) for item in literal_args}
                        if len(literal_types) == 1:
                            return next(iter(literal_types))
                        if bool in literal_types and int in literal_types:
                            return bool
                        return str
                if t_origin is not None:
                    return t_origin  # e.g., list for list[float]
                elif t in (float, int, str, bool, list, tuple):
                    return t
            return types[0] if types else None

        # Handle enum subclasses as strings
        if origin is None:
            if isinstance(annotation, type) and issubclass(annotation, Enum):
                return str
        return annotation

    def _pv_from_pydantic(
        self,
        prefix: str = SIM_PREFIX,
        identifier: str | None = None,
        cls: BaseModel | None = None,
        attr_name: Tuple[str] | str | None = None,
        exclude_attrs: List[str] = [],
    ) -> List[PVSchemaMetadata]:
        """Build PV metadata from a pydantic model class.

        Parameters
        ----------
        prefix : str, optional
            The PV name prefix to use, by default ``SIM``.
        identifier : str | None, optional
            An optional identifier to include in the PV name.
        cls : BaseModel | None, optional
            The pydantic model class from which to derive field metadata.
        attr_name : Tuple[str] | str | None, optional
            A path prefix to prepend to the schema attribute path.
        exclude_attrs : List[str], optional
            Field names to omit from the generated metadata.

        Returns
        -------
        List[PVSchemaMetadata]
            A list of metadata objects representing the PV fields.
        """
        metadata = []
        for fname, fproperties in cls.__pydantic_fields__.items():
            if fname in exclude_attrs:
                continue
            name = f"{prefix}-"
            if identifier:
                name += f"{identifier}:"
            if cls:
                name += f"{self._normalize_class_name(cls.__name__)}:"
            name += f"{fname.upper()}"
            if isinstance(attr_name, str):
                attr_name = (attr_name,)
            metadata.append(
                PVSchemaMetadata(
                    name=name,
                    type=self._resolve_single_type(fproperties.annotation),
                    # store path to attribute in schema
                    schema_attribute_path=(
                        (*attr_name, fname) if attr_name else (fname,)
                    ),
                )
            )
        return metadata


class ElementToPV(PVTranslator):
    """Translate a lattice element model into process variable metadata.

    This translator builds PV names and types for both simple element fields
    and nested fields such as twiss, sigma, centroid, and beam data.
    """

    def __init__(self, element: Element, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self._element = element
        complex_fields = ["twiss", "sigma", "centroid", "beam"]
        # always set the complex field attributes.
        [setattr(self, f"_{field}_metadata", []) for field in complex_fields]
        self._additional_metadata = []
        for fname in element.__pydantic_fields__:
            try:
                if fname in complex_fields:
                    # create PVMetadata for complex fields
                    value = getattr(self._element, fname)
                    result = self._pv_from_pydantic(
                        prefix=SIM_PREFIX,
                        identifier=self._element.name,
                        cls=value.__class__,
                        attr_name=fname,
                    )
                    setattr(self, f"_{fname}_metadata", result)
                else:
                    # create PVMetadata for simple element fields
                    self._additional_metadata.append(
                        self._pv_from_pydantic(
                            prefix=SIM_PREFIX,
                            identifier=self._element.name,
                            attr_name=fname,
                            exclude_attrs=[
                                "name",
                                "type",
                                "length",
                                "subtype",
                            ],
                        )
                    )
            except AttributeError:
                setattr(self, f"_{fname}_metadata", [])

    @cached_property
    def twiss_pvs(self) -> List[str]:
        return [pv.name for pv in self._twiss_metadata]

    @cached_property
    def sigma_pvs(self) -> List[str]:
        return [pv.name for pv in self._sigma_metadata]

    @cached_property
    def centroid_pvs(self) -> List[str]:
        return [pv.name for pv in self._centroid_metadata]

    @cached_property
    def beam_pvs(self) -> List[str]:
        return [pv.name for pv in self._beam_metadata]

    @cached_property
    def additional_pvs(self) -> List[str]:
        return [pv.name for pv in self._additional_metadata]

    @cached_property
    def element_pvs(self) -> List[str]:
        return (
            self.twiss_pvs
            + self.sigma_pvs
            + self.centroid_pvs
            + self.beam_pvs
            + self.additional_pvs
        )

    @cached_property
    def twiss_pv_types(self) -> Dict[str, Type]:
        return {pv.name: pv.type for pv in self._twiss_metadata}

    @cached_property
    def sigma_pv_types(self) -> Dict[str, Type]:
        return {pv.name: pv.type for pv in self._sigma_metadata}

    @cached_property
    def centroid_pv_types(self) -> Dict[str, Type]:
        return {pv.name: pv.type for pv in self._centroid_metadata}

    @cached_property
    def beam_pv_types(self) -> Dict[str, Type]:
        return {pv.name: pv.type for pv in self._beam_metadata}

    @cached_property
    def additional_pv_types(self) -> Dict[str, Type]:
        return {pv.name: pv.type for pv in self._additional_metadata}

    @cached_property
    def element_pv_types(self) -> Dict[str, Type]:
        return (
            self.twiss_pv_types
            | self.sigma_pv_types
            | self.centroid_pv_types
            | self.beam_pv_types
            | self.additional_pv_types
        )

    @cached_property
    def twiss_pv_metadata(self) -> List[PVSchemaMetadata]:
        return self._twiss_metadata

    @cached_property
    def sigma_pv_metadata(self) -> List[PVSchemaMetadata]:
        return self._sigma_metadata

    @cached_property
    def centroid_pv_metadata(self) -> List[PVSchemaMetadata]:
        return self._centroid_metadata

    @cached_property
    def beam_pv_metadata(self) -> List[PVSchemaMetadata]:
        return self._beam_metadata

    @cached_property
    def additional_pv_metadata(self) -> List[PVSchemaMetadata]:
        return self._additional_metadata

    @cached_property
    def element_pv_metadata(self) -> List[PVSchemaMetadata]:
        return (
            self.twiss_pv_metadata
            + self.sigma_pv_metadata
            + self.centroid_pv_metadata
            + self.beam_pv_metadata
            + self.additional_pv_metadata
        )


class GeneratorToPV(PVTranslator):
    """Translate generator model fields into PV metadata.

    This translator creates PV metadata for the generator settings used in
    lattice simulation definitions.
    """

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(self, *args, **kwargs)
        self._generator_metadata = self._pv_from_pydantic(
            cls=Generator,
            prefix=VM_PREFIX,
            exclude_attrs=["uuid"],
        )

    @cached_property
    def generator_pvs(self) -> List[str]:
        return [pv.name for pv in self._generator_metadata]

    @cached_property
    def generator_pv_types(self) -> Dict[str, Type]:
        return {pv.name: pv.type for pv in self._generator_metadata}

    @cached_property
    def generator_pv_metadata(self) -> List[PVSchemaMetadata]:
        return self._generator_metadata


class SectionToPV(PVTranslator):
    """Translate section-level model data into PV metadata.

    This translator generates PV metadata for section simulation configuration
    and initial conditions.
    """

    def __init__(self, section: Section | str = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if section is None:
            raise ValueError("SectionToPV requires a section or section name")
        # Normalize to section name string
        if isinstance(section, str):
            section_name = section
        elif isinstance(section, Section):
            section_name = section.name
        else:
            raise TypeError("section must be a Section instance or section name string")
        self._section = section_name
        self._code_metadata = [
            PVSchemaMetadata(
                name=f"{SIM_PREFIX}-{self._section}-SIMULATION:CODE",
                type=str,
                schema_attribute_path=("model",),
            )
        ]
        self._initial_condition_metadata = self._pv_from_pydantic(
            prefix=VM_PREFIX,
            identifier=f"{self._section}",
            cls=InitialConditions,
            attr_name=("initial_conditions",),
            exclude_attrs=["uuid"],
        )

    @cached_property
    def code_pvs(self) -> List[str]:
        return [pv.name for pv in self._code_metadata]

    @cached_property
    def initial_conditions_pvs(self) -> List[str]:
        return [pv.name for pv in self._initial_condition_metadata]

    @cached_property
    def section_pvs(self) -> List[str]:
        return self.code_pvs + self.initial_conditions_pvs

    @cached_property
    def code_pv_types(self) -> Dict[str, Type]:
        return {pv.name: pv.type for pv in self._code_metadata}

    @cached_property
    def initial_conditions_pv_types(self) -> Dict[str, Type]:
        return {pv.name: pv.type for pv in self._initial_condition_metadata}

    @cached_property
    def section_pv_types(self) -> Dict[str, Type]:
        return self.code_pv_types | self.initial_conditions_pv_types

    @cached_property
    def code_pv_metadata(self) -> Dict[str, Type]:
        return self._code_metadata

    @cached_property
    def initial_conditions_pv_metadata(self) -> Dict[str, Type]:
        return self._initial_condition_metadata

    @cached_property
    def section_pv_metadata(self) -> Dict[str, Type]:
        return self.code_pv_metadata + self.initial_conditions_pv_metadata


class LatticeToPV(PVTranslator):
    """Translate lattice-level model data into PV metadata.

    This translator builds PV metadata for lattice fields such as facility,
    initial conditions, and beam summary values.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._facility_metadata = PVSchemaMetadata(
            name=f"{SIM_PREFIX}-LATTICE:FACILITY",
            type=str,
            schema_attribute_path=("facility",),
        )
        self._apply_initial_conditions_metadata = PVSchemaMetadata(
            name=f"{VM_PREFIX}-INITIAL-CONDITIONS:ENABLE",
            type=str,
            schema_attribute_path=("set_initial_conditions",),
        )
        self._beam_summary_metadata = self._pv_from_pydantic(
            prefix=SIM_PREFIX,
            identifier="LATTICE",
            cls=BeamSummary,
            attr_name=("beam_summary",),
        )

    @cached_property
    def facility_pvs(self) -> List[str]:
        return [self._facility_metadata.name]

    @cached_property
    def apply_initial_conditions_pvs(self) -> List[str]:
        return [self._apply_initial_conditions_metadata.name]

    @cached_property
    def beam_summary_pvs(self) -> List[str]:
        return [pv.name for pv in self._beam_summary_metadata]

    @cached_property
    def lattice_pvs(self) -> List[str]:
        return (
            self.facility_pvs
            + self.apply_initial_conditions_pvs
            + self.beam_summary_pvs
        )

    @cached_property
    def facility_pv_types(self) -> Dict[str, Type]:
        return {self._facility_metadata.name: self._facility_metadata.type}

    @cached_property
    def apply_initial_conditions_pv_types(self) -> Dict[str, Type]:
        return {
            self._apply_initial_conditions_metadata.name: self._apply_initial_conditions_metadata.type
        }

    @cached_property
    def beam_summary_pv_types(self) -> Dict[str, Type]:
        return {pv.name: pv.type for pv in self._beam_summary_metadata}

    @cached_property
    def lattice_pv_types(self) -> Dict[str, Type]:
        return (
            self.facility_pv_types
            | self.apply_initial_conditions_pv_types
            | self.beam_summary_pv_types
        )

    @cached_property
    def facility_pv_metadata(self) -> PVSchemaMetadata:
        return self._facility_metadata

    @cached_property
    def apply_initial_conditions_pv_metadata(self) -> PVSchemaMetadata:
        return self._apply_initial_conditions_metadata

    @cached_property
    def beam_summary_pv_metadata(self) -> List[PVSchemaMetadata]:
        return self._beam_summary_metadata

    @cached_property
    def lattice_pv_metadata(self) -> List[PVSchemaMetadata]:
        return (
            self.facility_metadata
            + self.apply_initial_conditions_metadata
            + self.beam_summary_metadata
        )


class SimulationToPV(PVTranslator):
    """Translate simulation control fields into PV metadata.

    This translator is responsible for generating metadata for the simulation
    status, mode, trigger, and UUID PVs.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._status = PVMetadata(
            name=f"SIMULATION:STATUS",
            type=SimulationState,
        )
        self._mode = PVMetadata(
            name=f"SIMULATION:MODE",
            type=SimulationMode,
        )
        self._trigger = PVMetadata(
            name=f"SIMULATION:START",
            type=SimulationTrigger,
        )
        self._uuid = PVMetadata(
            name=f"SIMULATION:UUID",
            type=str,
        )
        self._simulation_metadata = [
            self._status,
            self._mode,
            self._trigger,
            self._uuid,
        ]

    @cached_property
    def simulation_pvs(self) -> List[str]:
        return [pv.name for pv in self._simulation_metadata]

    @cached_property
    def simulation_pv_types(self) -> Dict[str, Type]:
        return {pv.name: pv.type for pv in self._simulation_metadata}

    @cached_property
    def simulation_pv_metadata(self) -> List[PVMetadata]:
        return self._simulation_metadata

    @cached_property
    def status_pv(self) -> PVMetadata:
        return self._status

    @cached_property
    def mode_pv(self) -> PVMetadata:
        return self._mode

    @cached_property
    def start_pv(self) -> PVMetadata:
        return self._trigger

    @cached_property
    def uuid_pv(self) -> PVMetadata:
        return self._uuid
