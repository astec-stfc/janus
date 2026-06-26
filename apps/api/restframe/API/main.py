import os
import json
from collections import Counter
from typing import Annotated, Dict, Union, Any
import base64
import toml

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import HTMLResponse
from fastapi.middleware.gzip import GZipMiddleware
from kafka import KafkaProducer

from pydantic import BaseModel

from data.SimFrame import SimFrame_Interface
from janus_common.schemas.elements import Lattice
from janus_common.utils import constants
from janus_common.utils.flow_log import flow_log
from laura.models.element import PhysicalBaseElement

import logging


class EndpointFilter(logging.Filter):
    def __init__(
        self,
        path: str,
        *args: Any,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self._path = path

    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find(self._path) == -1


# Load configuration from config.toml
config_path = os.path.join(os.path.dirname(__file__), "config.toml")
if not os.path.exists(config_path):
    raise FileNotFoundError(f"Configuration file not found: {config_path}")
with open(config_path, "r") as config_file:
    config = toml.load(config_file)
print(f"Configuration loaded from {config_path}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global master_framework, kafka_producer, tracking_finished_state

    # Initialize Kafka producer
    kafka_producer = KafkaProducer(
        bootstrap_servers=f"{constants.BOOTSTRAP_SERVERS}:{constants.KAFKA_PORT}",
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    tracking_finished_state = False

    # load facility from environment variable
    facility = os.getenv("FACILITY", "CLARA")
    # facility = config['General'].get("facility")
    runs_directory = config[facility].get("runs_directory")
    settings_file = config[facility].get("settings_file")
    master_lattice = config[facility].get("master_lattice", None)
    screen_directory = config[facility].get("screen_directory", None)
    particle = config[facility].get(
        "particle", "electron"
    )  # Default to electron if not specified
    print(
        f"""Starting SimFrame Interface with facility: {facility}
        \truns_directory: {runs_directory}
        \tsettings_file: {settings_file}
        \tmaster_lattice: {master_lattice}
        \tscreen_directory: {screen_directory}
        \tParticle: {particle}""",
        flush=True,
    )
    if not os.path.isdir(runs_directory):
        os.makedirs(runs_directory, exist_ok=True)
    master_framework = SimFrame_Interface(
        runs_directory=runs_directory,
        settings_file=settings_file,
        master_lattice=master_lattice,
        screen_directory=screen_directory,
        particle=particle,
        facility=facility,
    )
    master_framework.start_tracking()
    master_framework.set_lattice_update_flag(
        master_framework.track_uuid, master_framework.track_startfile, force=True
    )
    yield

    # Cleanup
    if kafka_producer:
        kafka_producer.close()


app = FastAPI(lifespan=lifespan)
app.add_middleware(GZipMiddleware)


@app.get("/")
def read_root() -> dict:
    return {}


@app.post("/new")
def create_simframe_instance(clean: bool = False) -> dict:
    if clean:
        master_framework.reset_lattice()
    return {"clean": clean}


@app.get("/lattice")
def get_lattice() -> dict:
    """Returns a dict of the lattice properties.
    {
        'name': str,
        'parameter': str,
        'units': str,
        'value': int | float | str,
        'type': 'quadrupole' | 'screen',
        'facility': str,
        'machine_area': str,
        'beamp': int | float
    }
    """
    return master_framework.get_lattice().model_dump()


@app.get("/diagnostics/physical-element-types")
def get_physical_element_types() -> dict:
    elements = [
        elem
        for elem in master_framework.framework.machine.elements.values()
        if isinstance(elem, PhysicalBaseElement)
    ]
    type_counts = Counter(elem.hardware_type for elem in elements)

    return {
        "facility": master_framework.facility,
        "total": len(elements),
        "type_counts": dict(sorted(type_counts.items())),
    }


@app.get("/diagnostics/physical-elements")
def get_physical_elements(
    layout: str,
    include: Annotated[list[str] | None, Query()] = None,
) -> dict:
    machine = master_framework.framework.machine  # LAURA model
    available_layouts = sorted(machine.lattices)
    if layout not in machine.lattices:
        raise HTTPException(
            status_code=400,
            detail={
                "unknown_layout": layout,
                "available_layouts": available_layouts,
            },
        )

    physical_elements = [
        machine.elements[name]
        for name in machine.elements_between(path=layout)
        if isinstance(machine.elements[name], PhysicalBaseElement)
    ]
    available_types = {elem.hardware_type for elem in physical_elements}
    requested_types = set(include) if include is not None else available_types
    unknown_types = sorted(requested_types - available_types)
    if unknown_types:
        raise HTTPException(
            status_code=400,
            detail={
                "unknown_types": unknown_types,
                "available_types": sorted(available_types),
            },
        )

    elements = []
    for elem in physical_elements:
        elem_type = elem.hardware_type
        if elem_type in requested_types:
            elements.append(
                {
                    "name": elem.name,
                    "type": elem_type,
                    "start": elem.start.z,
                    "end": elem.end.z,
                }
            )

    return {
        "facility": master_framework.facility,
        "layout": layout,
        "elements": sorted(
            elements,
            key=lambda elem: (elem["start"], elem["end"], elem["name"]),
        ),
    }


@app.post("/lattice")
def set_lattice(lattice: Lattice) -> dict:
    """Returns a dict of the lattice properties.
    {
        'name': str,
        'parameter': str,
        'units': str,
        'value': int | float | str,
        'type': 'quadrupole' | 'screen',
        'facility': str,
        'machine_area': str,
        'beamp': int | float
    }
    """
    master_framework.set_lattice_elements(lattice)
    return lattice.model_dump()


@app.get("/uuid")
def get_uuid() -> dict:
    """Returns a dict of the uuid.
    {
        'uuid': str,
    }
    """
    return {"uuid": master_framework.get_track_uuid()}


@app.get("/info")
def get_object_properties(object: str, parameter: Union[str, None] = None) -> dict:
    """Returns a dict of the object properties.
    {
        'parameter': str,
        'value': int | float | str,
    }
    """
    d = {"object": object}
    d.update(master_framework.put_object_properties(object, parameter))
    return d


@app.post("/info")
def put_object_properties(
    object: str, parameter: str, value: Union[int, float, str]
) -> dict:
    """Sets the property value and returns a dict of the object properties.
    {
        'parameter': str,
        'value': int | float | str,
        'set_value': int | float | str,
        'original_value': int | float | str
    }
    """
    d = {"object": object}
    d.update(master_framework.put_object_properties(object, parameter, value))
    return d


class simframeItem(BaseModel):
    name: str
    parameter: str | None = None
    value: int | float | str | None = None


@app.post("/info/json")
def put_object_properties_json(object: simframeItem) -> dict:
    """Return a dict of the object properties.
    If value is not None, also sets the property value.
        {
            'parameter': str,
            'value': int | float | str,
            Optional['set_value': int | float | str ],
            Optional['original_value': int | float | str ],
        }
    """
    d = {}
    d.update(
        master_framework.put_object_properties(
            object.name, object.parameter, object.value
        )
    )
    return d


@app.get("/settings")
def get_settings_filename() -> dict:
    """Returns a dict of the settings filename.
    {
        'settings': str,
    }
    """
    d = {}
    d.update(master_framework.get_settings_filename())
    return d


@app.post("/ncpu")
def set_parallel_cpu_number(cpu: int) -> dict:
    """Sets the number of parallel CPU threads to use for tracking. Returns a dict.
    {
        'ncpu': int,
    }
    """
    d = {}
    d.update(master_framework.set_parallel_cpu_number(cpu))
    return d


@app.post("/track")
def start_tracking(
    end_lattice: Union[str, None] = "S07",
    rerun: bool = False,
    client_id: str = None,
    request_id: str = None,
) -> dict:
    """Starts tracking and returns tracking_status as a dict."""
    global tracking_finished_state
    tracking_finished_state = False
    flow_log(
        "G04 tracking.publish",
        "S3/6",
        client_id=client_id,
        request_id=request_id,
        current="restframe received tracking request, publishing to topic 'tracking_started' and running simulation",
        next_step="lattice-to-epics to consume from topic 'tracking_started' and set SIMULATION:STATUS in EPICS",
    )

    # Publish tracking started event
    kafka_producer.send(
        "tracking_started",
        value={
            "request_id": request_id,
            "client_id": client_id,
        },
    )

    d = {}
    d.update(master_framework.start_tracking(endfile=end_lattice, rerun=rerun))
    uuid = master_framework.get_track_uuid()
    flow_log(
        "G06 tracking.done",
        "S4/6",
        client_id=client_id,
        request_id=request_id,
        current="simulation complete, publishing to topic 'tracking_finished'",
        next_step="comm-to-restframe to fetch completed results and POST them to the lattice API",
    )
    kafka_producer.send(
        "tracking_finished",
        value={
            "request_id": request_id,
            "uuid": uuid,
            "client_id": client_id,
        },
    )
    return d


@app.get("/track")
def get_tracking_status(end_lattice: Union[str, None] = None) -> dict:
    """Returns progress of the tracking method as a dict.
    {
        'progress': float,
        'finished_tracking': bool
        Optional['momentum': {'magnet_name>': <momentum_eV>,...}]
    }
    """
    global tracking_finished_state
    d = {}
    d.update(master_framework.get_tracking_status())

    return d


@app.get("/results/screens")
def get_screens() -> dict:
    """Returns a list of screen names as a dict.
    {
        'screens': [<screen_name>, ...]
    }
    """
    d = {}
    d.update(master_framework.get_screens())
    return d


@app.get("/results/bpms")
def get_bpms() -> dict:
    """Returns a list of bpm names as a dict.
    {
        'bpms': [<bpm_name>, ...]
    }
    """
    d = {}
    d.update(master_framework.get_bpms())
    print(d)
    return d


@app.get("/results/twiss/{element}")
def get_element_twiss(element: str):
    """Returns a dictionary of twiss parameter at an element location.
    {
        '<twiss_variable>': <twiss_value>,
        ...
    }
    """
    d = {}
    d.update(master_framework.get_element_twiss(element))
    return d


@app.get("/results/magnets/momentum")
def get_magnet_momentum() -> dict:
    """Returns a dictionary of magnet names and beam momenta in eV.
    {
        '<magnet_name>': <momentum_eV>,
        ...
    }
    """
    d = {}
    d.update(master_framework.get_magnet_momentum())
    return d


@app.get(
    "/results/image/{screen}",
    responses={200: {"content": {"image/png": {}}}},
    response_class=Response,
)
def get_screen_image(screen: str, force: bool = False) -> Response:
    """Returns a PNG image as a FastAPI Response object."""
    image_bytes: bytes = master_framework.get_screen_image(screen, force)
    if not image_bytes and not force:
        raise HTTPException(status_code=410, detail="Screen not updated")
    else:
        return Response(content=base64.b64decode(image_bytes), media_type="image/png")


@app.get(
    "/results/bpms/{bpm}",
)
def get_bpm_centroids(bpm: str, force: bool = False) -> Response:
    """Returns a PNG image as a FastAPI Response object."""
    twiss = master_framework.get_element_twiss(bpm)
    if twiss is not None:
        centroids: Dict[str, float] = {"x": twiss.mean_x, "y": twiss.mean_y}
    else:
        centroids = None
    if not centroids and not force:
        raise HTTPException(status_code=410, detail="BPM not updated")
    else:
        return centroids


HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="content-type" content="text/html; charset=UTF-8">
    <title>My Project - ReDoc</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="shortcut icon" href="https://fastapi.tiangolo.com/img/favicon.png">
    <style>
        body {
            margin: 0;
            padding: 0;
        }
    </style>
    <style data-styled="" data-styled-version="4.4.1"></style>
</head>
<body>
    <div id="redoc-container"></div>
    <script src="https://cdn.jsdelivr.net/npm/redoc/bundles/redoc.standalone.js"> </script>
    <script>
        var spec = %s;
        Redoc.init(spec, {}, document.getElementById("redoc-container"));
    </script>
</body>
</html>
"""


@app.get("/html_docs", response_class=HTMLResponse)
def html_docs() -> str:
    """Returns an html version of the docs."""
    return HTML_TEMPLATE % json.dumps(app.openapi())
