"""Build shared process variables from Python and pydantic types.

This module provides utilities for constructing process variable (PV) objects
from Python primitive types, ``typing`` annotations, enums, and pydantic
models. It supports scalar PVs, enum PVs, and automatic conversion of model
fields to PV metadata.
"""

import builtins
from typing import Any, Dict, List, Literal, Optional, get_args, get_origin, Union
from types import UnionType
from enum import Enum
from pydantic import BaseModel
from p4p.server.thread import SharedPV
from p4p.nt import NTScalar, NTEnum
from .handlers import BasicHandler, EnumHandler, time_in_seconds_and_nanoseconds
TYPE_MAP = {
    int: ("i", 0),
    float: ("d", 0.0),
    str: ("s", ""),
    bool: ("b", False),
    list: ("ad", []),
    tuple: ("ad", []),
}


class Builder:
    """Create shared PV instances from type information.

    The builder supports creating scalar PVs and enum PVs from Python types,
    ``Literal`` annotations, and pydantic model field definitions.
    """

    def __init__(self, *args, **kwargs):
        """Initialize a Builder instance."""
        pass

    def _is_native_type(self, t) -> bool:
        """Return whether a type is a built-in native Python type.

        Parameters
        ----------
        t : Any
            The type to inspect.

        Returns
        -------
        bool
            ``True`` if the type is a Python built-in native type, otherwise
            ``False``.
        """
        return (
            isinstance(t, type)
            and t.__name__ in dir(builtins)
            and getattr(
                builtins,
                t.__name__,
                None,
            )
            is t
        )

    def _make_initial_scalar_value(
        self, value: Any, description: str = ""
    ) -> Dict[str, Any]:
        """Build an initial scalar PV payload with a timestamp.

        Parameters
        ----------
        value : Any
            The initial PV value.
        description : str, optional
            A display description for the PV, by default an empty string.

        Returns
        -------
        Dict[str, Any]
            A dictionary containing initial PV data, including timestamp and
            display metadata.
        """
        seconds, nanoseconds = time_in_seconds_and_nanoseconds()
        return {
            "value": value,
            "display.description": description,
            "timeStamp.secondsPastEpoch": seconds,
            "timeStamp.nanoseconds": nanoseconds,
        }

    def resolve_single_type(self, annotation):
        """Resolve a typing annotation to a concrete Python type.

        Parameters
        ----------
        annotation : Any
            A type annotation, possibly a ``Union`` or a PEP 604 union.

        Returns
        -------
        Any
            The resolved Python type used to create a PV, or ``None`` if the
            annotation cannot be resolved.
        """
        origin = get_origin(annotation)
        # Handle Union[...] types and | (PEP 604)
        if origin is Union or origin is UnionType:
            types = [t for t in get_args(annotation) if t is not type(None)]
            for t in types:
                t_origin = get_origin(t)
                if isinstance(t, type) and issubclass(t, Enum):
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

    def make_scalar_pv(
        self,
        nt_code,
        default_value,
    ) -> SharedPV:
        """Create a scalar SharedPV with the specified native type code.

        Parameters
        ----------
        nt_code : str
            The NTScalar native type code.
        default_value : Any
            The initial default value for the PV.

        Returns
        -------
        SharedPV
            A new scalar shared PV instance.
        """
        nt = NTScalar(nt_code, display=True)
        handler = BasicHandler()
        initial = self._make_initial_scalar_value(default_value)
        return SharedPV(nt=nt, initial=initial, handler=handler)

    def make_enum_pv(
        self,
        read_pv: Optional[SharedPV] = None,
        read_only: bool = False,
        choices: Optional[List[str]] = ["OFF", "ON"],
        read_values: Optional[List[int]] = None,
    ):
        """Create an enum-based SharedPV.

        Parameters
        ----------
        read_pv : Optional[SharedPV], optional
            Optional PV used to read a backing value, by default None.
        read_only : bool, optional
            Whether the enum PV should be read-only, by default False.
        choices : Optional[List[str]], optional
            The list of allowed enum string values, by default ["OFF", "ON"].
        read_values : Optional[List[int]], optional
            Optional integer values corresponding to choices, by default None.

        Returns
        -------
        SharedPV
            A new enum shared PV instance.
        """
        seconds, nanoseconds = time_in_seconds_and_nanoseconds()
        initial = NTEnum.buildType()()
        initial.value.index = 0
        initial.value.choices = choices
        initial.timeStamp = {
            "secondsPastEpoch": seconds,
            "nanoseconds": nanoseconds,
            "userTag": 0,
        }
        options = {
            "read_pv": read_pv,
            "read_values": read_values,
        }

        return SharedPV(
            handler=EnumHandler(options, read_only=read_only), initial=initial
        )

    def make_shared_pv_from_type(
        self,
        py_type,
        choices: List[str] = None,
        initial_value=None,
    ) -> SharedPV:
        """Create a SharedPV instance based on a Python type annotation.

        Parameters
        ----------
        py_type : Any
            The Python type or typing annotation to convert into a PV.
        choices : List[str], optional
            Choices to use for enum-like types, by default None.
        initial_value : Any, optional
            An optional initial value for scalar PVs, by default None.

        Returns
        -------
        SharedPV
            The constructed shared PV for the provided type.

        Raises
        ------
        ValueError
            If a ``Literal`` annotation is unsupported or mixes incompatible
            literal value types.
        """

        if py_type in TYPE_MAP:
            nt_code, default = TYPE_MAP[py_type]
            return self.make_scalar_pv(nt_code, default)

        elif isinstance(py_type, type) and issubclass(py_type, Enum):
            enum_choices = choices or [e.name for e in py_type]
            return self.make_enum_pv(choices=enum_choices)

        elif get_origin(py_type) is Literal:
            literal_values = get_args(py_type)
            if not literal_values:
                raise ValueError("Literal type must have at least one value")

            if not all(isinstance(val, (str, int, float)) for val in literal_values):
                raise ValueError(
                    f"Literal types only support str, int, or float values."
                )
            value_types = {type(v) for v in literal_values}
            if len(value_types) != 1:
                raise ValueError(f"Literal contains mixed types: {value_types}")
            value_type = next(iter(value_types))
            if value_type is str:
                return self.make_enum_pv(choices=list(literal_values))
            if value_type in (int, float):
                nt_code, _ = TYPE_MAP[value_type]
                return self.make_scalar_pv(
                    nt_code,
                    literal_values[0],
                    initial_value,
                )
            raise ValueError(f"Unsupported Literal type: {value_type}")

    def convert_non_native_types_to_pvs(
        self,
        pv_name: str,
        field: BaseModel,
    ) -> Dict[str, SharedPV]:
        """Convert a pydantic model's fields into shared PVs.

        Parameters
        ----------
        pv_name : str
            The base PV name to use for the converted fields.
        field : BaseModel
            The pydantic model containing fields to convert.

        Returns
        -------
        Dict[str, SharedPV]
            A mapping from the provided PV name to the created PV instance.
            Returns ``None`` if the provided field is not a pydantic model.
        """
        if not isinstance(field, BaseModel):
            return
        pvs = {}
        for _, field_properties in field.__pydantic_fields__.items():
            # Get the type from pydantic TypeInfo so we can make the right type PV
            field_type = self.resolve_single_type(field_properties.annotation)
            pvs[pv_name] = self.make_shared_pv_from_type(py_type=field_type)
        return pvs
