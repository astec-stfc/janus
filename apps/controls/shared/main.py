import random
import time
import os
from types import UnionType
from typing import Dict, List, Optional, Literal
import builtins
from p4p.nt import NTScalar, NTEnum
from p4p.server import Server, ServerOperation
from pydantic_core import PydanticUndefined

from schemas import elements
from p4p.server.thread import SharedPV
import requests
from typing import get_args, get_origin, Union
from enum import Enum

abbreviations = {
    "alpha_x": "ALPHA:X",
    "beta_x": "BETA:X",
    "alpha_y": "ALPHA:Y",
    "beta_y": "BETA:Y",
    "energy": "ENERGY",
    "charge": "CHARGE",
    "n_particles": "PARTICLE:COUNT",
    "momentum": "MOMENTUM",
    "emittance_x": "EMIT:X",
    "emittance_y": "EMIT:Y",
    "normalised_emittance_x": "NEMIT:X",
    "normalised_emittance_y": "NEMIT:Y",
    "sigma_x": "SIG:X",
    "sigma_y": "SIG:Y",
    "centroids_x": "CENTROID:X",
    "centroids_y": "CENTROID:Y",
    "position": "POSITION",
    "cov_xx": "COV:XX",
    "cov_yy": "COV:YY",
    "cov_xxp": "COV:XXP",
    "cov_yyp": "COV:YYP",
    "cov_xy": "COV:XY",
    "cov_xyp": "COV:XYP",
}


class LatticeAPI:
    """
    Placeholder for the Lattice API.
    This should be replaced with actual API calls to fetch data.
    """

    def __init__(
        self,
        hostname: str = "lattice_api",
        port: int = 5000,
        version: str = "v1",
    ):
        if hostname:
            self.hostname = hostname
        if port:
            self.port = port
        if version:
            self.version = version

    @property
    def sections(self):
        response = requests.get(
            f"http://{self.hostname}:{self.port}/{self.version}"
            + "/lattice/sections/names",
        )
        if response.status_code != 200:
            raise Exception(
                "Failed to fetch sections from Lattice API: "
                + f"{response.status_code} {response.text}"
            )
        return response.json()

    @property
    def lattice(self) -> elements.Lattice:
        response = requests.get(
            f"http://{self.hostname}:{self.port}/{self.version}/lattice"
        )
        if response.status_code != 200:
            raise Exception(
                "Failed to fetch sections from Lattice API: "
                + f"{response.status_code} {response.text}"
            )
        return elements.Lattice.model_validate(response.json())

    @property
    def beam_info(self):
        return abbreviations.keys()


def time_in_seconds_and_nanoseconds(timestamp: float):
    seconds = int(timestamp // 1)
    nanoseconds = int((timestamp % 1) * 1e9)
    return seconds, nanoseconds


def get_server_conf():
    server_port = str(os.getenv("EPICS_PVAS_SERVER_PORT", 6090))
    client_port = str(os.getenv("EPICS_PVA_SERVER_PORT", 6090))
    broadcast_port = str(os.getenv("EPICS_PVAS_BROADCAST_PORT", 6090))
    auto_addr_list = str(os.getenv("EPICS_PVA_AUTO_ADDR_LIST", "NO"))
    addr_list = str(os.getenv("EPICS_PVA_ADDR_LIST", ""))
    interface_addr_list = str(os.getenv("EPICS_PVA_INTF_ADDR_LIST", ""))
    conf = {
        "EPICS_PVAS_BROADCAST_PORT": broadcast_port,
        "EPICS_PVAS_SERVER_PORT": server_port,
        "EPICS_PVA_ADDR_LIST": addr_list,
        "EPICS_PVA_AUTO_ADDR_LIST": auto_addr_list,
        "EPICS_PVA_SERVER_PORT": client_port,
        "EPICS_PVA_INTF_ADDR_LIST": interface_addr_list,
    }
    return conf


class EnumHandler:
    def __init__(
        self,
        options: Optional[Dict] = None,
        read_only: bool = False,
    ):
        self.read_only = read_only
        self.read_pv = options["read_pv"]
        self.read_values = options["read_values"]

    def put(self, pv, op):
        if self.read_only:
            op.done(error=f"{op.name()} is read_only")
        if not op.value().changed("timeStamp"):
            seconds, nanoseconds = time_in_seconds_and_nanoseconds(time.time())
            op.value()["timeStamp"] = {
                "secondsPastEpoch": seconds,
                "nanoseconds": nanoseconds,
                "userTag": 0,
            }
        pv.post(op.value())
        delay = random.uniform(1, 2)
        time.sleep(delay)
        if self.read_pv is not None:
            read_value = self.read_values[op.value()["value"]["index"]]
            self.read_pv.post(read_value)
        op.done()


class Handler:
    def put(self, pv: SharedPV, op: ServerOperation):
        # Note that timestamps are not automatically
        # handled so we may need to set them ourselves
        if not op.value().raw.changed("timeStamp"):
            timestamp = time.time()
            pv.post(
                op.value(), timestamp=timestamp
            )  # just store and update subscribers
        else:
            pv.post(op.value())
        op.done()


class EnumBuilder:

    def __init__(self):
        self.seconds, self.nanoseconds = time_in_seconds_and_nanoseconds(
            time.time(),
        )
        self.initial_values = {
            "value": 0,
            "display.description": "",
            "timeStamp.secondsPastEpoch": self.seconds,
            "timeStamp.nanoseconds": self.nanoseconds,
        }

    def make_pv(
        self,
        read_pv: Optional[SharedPV] = None,
        read_only: bool = False,
        choices: Optional[List[str]] = ["OFF", "ON"],
        read_values: Optional[List[int]] = None,
    ):
        initial = NTEnum.buildType()()
        initial.value.index = 0
        initial.value.choices = choices
        initial.timeStamp = {
            "secondsPastEpoch": self.seconds,
            "nanoseconds": self.nanoseconds,
            "userTag": 0,
        }
        options = {
            "read_pv": read_pv,
            "read_values": read_values,
        }

        return SharedPV(
            handler=EnumHandler(options, read_only=read_only), initial=initial
        )


def resolve_single_type(annotation):
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


def make_shared_pv_from_type(
    py_type,
    initial_value=None,
    choices=None,
    handler=None,
):
    """
    Create a SharedPV with the correct NT type
    based on the provided Python type.
    """
    if handler is None:
        handler = Handler()
    seconds, nanoseconds = time_in_seconds_and_nanoseconds(time.time())
    if py_type is int:
        nt = NTScalar("i", display=True)
        initial = {
            "value": initial_value if initial_value is not None else 0,
            "display.description": "",
            "timeStamp.secondsPastEpoch": seconds,
            "timeStamp.nanoseconds": nanoseconds,
        }
        return SharedPV(nt=nt, initial=initial, handler=handler)
    elif py_type is float:
        nt = NTScalar("d", display=True)
        initial = {
            "value": initial_value if initial_value is not None else 0.0,
            "display.description": "",
            "timeStamp.secondsPastEpoch": seconds,
            "timeStamp.nanoseconds": nanoseconds,
        }
        return SharedPV(nt=nt, initial=initial, handler=handler)
    elif py_type is str:
        nt = NTScalar("s", display=True)
        initial = {
            "value": initial_value if initial_value is not None else "",
            "display.description": "",
            "timeStamp.secondsPastEpoch": seconds,
            "timeStamp.nanoseconds": nanoseconds,
        }
        return SharedPV(nt=nt, initial=initial, handler=handler)
    elif py_type is bool:
        nt = NTScalar("b", display=True)
        initial = {
            "value": initial_value if initial_value is not None else False,
            "display.description": "",
            "timeStamp.secondsPastEpoch": seconds,
            "timeStamp.nanoseconds": nanoseconds,
        }
        return SharedPV(nt=nt, initial=initial, handler=handler)
    elif py_type is list or py_type is tuple:
        nt = NTScalar("ad", display=True)
        initial = {
            "value": initial_value if initial_value is not None else [],
            "display.description": "",
            "timeStamp.secondsPastEpoch": seconds,
            "timeStamp.nanoseconds": nanoseconds,
        }
        return SharedPV(nt=nt, initial=initial, handler=handler)
    elif isinstance(py_type, type) and issubclass(py_type, Enum):
        builder = EnumBuilder()
        enum_choices = choices or [e.name for e in py_type]
        return builder.make_pv(choices=enum_choices)
    elif get_origin(py_type) is Literal:
        # Handle typing.Literal types
        literal_values = get_args(py_type)

        if not literal_values:
            raise ValueError("Literal type must have at least one value")

        # Determine the base type from the literal values
        value_types = set(type(val) for val in literal_values)

        if not all(isinstance(val, (str, int, float)) for val in literal_values):
            raise ValueError(
                f"Literal types only support str, int, or float values. "
                f"Got types: {value_types}"
            )

        # If all values are strings
        if all(isinstance(val, str) for val in literal_values):
            # Use the same approach as EnumBuilder for NTEnum
            builder = EnumBuilder()
            enum_choices = [value for value in literal_values]
            return builder.make_pv(choices=enum_choices)

        # If all values are integers
        elif all(isinstance(val, int) for val in literal_values):
            nt = NTScalar("i", display=True)
            initial = {
                "value": (
                    initial_value if initial_value is not None else literal_values[0]
                ),
                "display.description": "",
                "timeStamp.secondsPastEpoch": seconds,
                "timeStamp.nanoseconds": nanoseconds,
            }
            return SharedPV(nt=nt, initial=initial, handler=handler)

        # If all values are floats
        elif all(isinstance(val, float) for val in literal_values):
            nt = NTScalar("d", display=True)
            initial = {
                "value": (
                    initial_value if initial_value is not None else literal_values[0]
                ),
                "display.description": "",
                "timeStamp.secondsPastEpoch": seconds,
                "timeStamp.nanoseconds": nanoseconds,
            }
            return SharedPV(nt=nt, initial=initial, handler=handler)

        else:
            raise ValueError(
                f"Literal contains mixed types: {value_types}. "
                f"All values must be of the same type."
            )
    else:
        raise ValueError(f"Unsupported type: {py_type}")


def convert_non_native_types_to_pvs(
    element_name: str,
    field: elements.Twiss | elements.Sigma | elements.Centroid,
) -> Dict[str, SharedPV]:
    if (
        field is not elements.Twiss
        and field is not elements.Sigma
        and field is not elements.Centroid
        and field is not elements.Beam
    ):
        return
    pvs = {}
    for field_name, field_properties in field.__pydantic_fields__.items():
        # Construct a PV name from the field
        pv_name = (
            f"SIM-{element_name}:{field.__name__.upper()}:"
            + f"{field_name.capitalize()}"
        )
        # Get the type from pydantic TypeInfo so we can make the right type PV
        field_type = resolve_single_type(field_properties.annotation)
        pvs[pv_name] = make_shared_pv_from_type(py_type=field_type)
    return pvs


def is_native_type(t):
    """Check if t is a native type"""
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


def construct_pvs_from_lattice(lattice: elements.Lattice) -> Dict[
    str,
    SharedPV,
]:
    """
    Converts fields for each element into SharedPVs,
    non-native types are deconstructed into native types
    """
    shared_pvs = {}
    for element in lattice.get_elements():
        fields = {
            field_name: field
            for field_name, field in element.__class__.model_fields.items()
            if field_name in element.model_fields_set
        }
        for field_name, field in fields.items():
            field_type = resolve_single_type(field.annotation)
            if is_native_type(field_type):
                pv_name = f"SIM-{element.name}:{field_name.capitalize()}"
                shared_pvs[pv_name] = make_shared_pv_from_type(
                    py_type=field_type,
                )
            else:
                match field_name:
                    case "twiss":
                        pvs = convert_non_native_types_to_pvs(
                            element_name=element.name,
                            field=elements.Twiss,
                        )
                    case "sigma":
                        pvs = convert_non_native_types_to_pvs(
                            element_name=element.name,
                            field=elements.Sigma,
                        )
                    case "centroid":
                        pvs = convert_non_native_types_to_pvs(
                            element_name=element.name,
                            field=elements.Centroid,
                        )
                    case "beam":
                        pvs = convert_non_native_types_to_pvs(
                            element_name=element.name,
                            field=elements.Beam,
                        )
                if pvs:
                    shared_pvs.update(pvs)
    return shared_pvs


def main():
    # query API to get list of sections
    lattice = LatticeAPI()
    pvs = construct_pvs_from_lattice(lattice.lattice)
    builder = EnumBuilder()

    pvs["SIMULATION:STATUS_RBV"] = make_shared_pv_from_type(
        py_type=int,
        initial_value=0,
    )
    pvs["SIMULATION:STATUS"] = builder.make_pv(
        read_pv=pvs["SIMULATION:STATUS_RBV"],
        read_only=False,
        choices=[
            "COMPLETE",
            "TRACKING",
            "ERROR",
        ],
        read_values=[
            0,
            1,
            2,
        ],
    )
    pvs["SIMULATION:MODE"] = builder.make_pv(
        read_only=False,
        choices=[
            "AUTO",
            "TRIGGER",
        ],
        read_values=[
            0,
            1,
        ],
    )
    pvs["SIMULATION:START"] = builder.make_pv(
        read_only=False,
        choices=[
            "BYPASS",
            "ACTIVATE",
        ],
        read_values=[
            0,
            1,
        ],
    )
    lattice_instance: elements.Lattice = lattice.lattice
    sim_code_name = f"SIM-{lattice_instance.facility}:UUID"
    initial_code_value = ""
    sim_code_pv = make_shared_pv_from_type(
        py_type=str,
        initial_value=initial_code_value,
    )
    pvs[sim_code_name] = sim_code_pv
    for section in lattice_instance.get_sections():
        sim_code_name = f"VM-{section.name}-SIMULATION:CODE"
        initial_code_value = section.model if section.model is not None else ""
        sim_code_pv = make_shared_pv_from_type(
            py_type=str,
            initial_value=initial_code_value,
        )
        pvs[sim_code_name] = sim_code_pv
        for tw in ["beta", "alpha", "nemit"]:
            for plane in ["x", "y"]:
                suffix = f"{tw.upper()}_{plane.upper()}"
                name = f"SIM-{section.name}-INITIAL-CONDITIONS:{suffix}"
                pv = make_shared_pv_from_type(py_type=float, initial_value=None)
                pvs[name] = pv
        name = f"SIM-{lattice_instance.facility}-INITIAL-CONDITIONS:ENABLE"
        pv = make_shared_pv_from_type(py_type=str, initial_value="")
        pvs[name] = pv
    for field_name, field_properties in elements.Generator.__pydantic_fields__.items():
        if field_name not in ["uuid"]:
            pv_name = f"SIM-GENERATOR:{field_name.upper().replace('_', '-')}"
            if field_properties.annotation in [int, bool, float]:
                field_type = resolve_single_type(field_properties.annotation)
            else:
                field_type = str
            pvs[pv_name] = make_shared_pv_from_type(py_type=field_type)
    for beam in lattice.beam_info:
        suffix = abbreviations.get(beam, beam.upper())
        name = f"VM-{lattice_instance.facility}-{suffix}"
        pv = make_shared_pv_from_type(py_type=list, initial_value=[])
        pvs[name] = pv
    conf = get_server_conf()
    with Server(providers=[pvs], conf=conf) as server:
        while True:
            try:
                time.sleep(1)  # Keep the server running
            except KeyboardInterrupt:
                print("Server stopped by user.")
                server.stop()

                break


if __name__ == "__main__":
    main()
