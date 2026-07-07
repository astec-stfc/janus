from typing import Any, List, Dict
import requests
from janus_common.utils import constants
from janus_common.schemas.elements import Lattice

_session = requests.Session()


# -------------- SEED/POST requests --------------
from time import perf_counter

def add_lattice(lattice: Lattice, request_id: str = None):
    """Submit a lattice over the legacy JSON API path.

    This remains useful for settings-oriented flows, but tracked result payloads
    should prefer :func:`add_lattice_binary` to avoid re-serializing large arrays
    into JSON.
    """
    url = (
        f"http://{constants.HOST_LATTICE_API}:"
        + f"{constants.PORT_COMMS}"
        + "/v1/lattice/"
    )
    params = {"request_id": request_id} if request_id else None

    t0 = perf_counter()
    response = requests.post(url, json=lattice.model_dump(), params=params)
    t1 = perf_counter()

    print(
        "add_lattice timings ",
        f"uuid={lattice.uuid} ",
        f"serialize_post={t1-t0:.3f}s ",
        f"status={response.status_code}",
    )
    response.raise_for_status()


def add_lattice_binary(
    binary_payload: bytes,
    client_id: str,
    request_id: str = None,
) -> dict:
    """Submit a completed lattice as raw binary transport bytes.

    This is the preferred post-tracking handoff because it forwards the shared
    binary lattice representation directly to lattice-api for one decode there.
    """
    url = (
        f"http://{constants.HOST_LATTICE_API}:"
        + f"{constants.PORT_COMMS}"
        + "/v1/lattice/binary"
    )
    params = {"client_id": client_id}
    if request_id:
        params["request_id"] = request_id

    t0 = perf_counter()
    response = requests.post(
        url,
        data=binary_payload,
        params=params,
        headers={"Content-Type": "application/octet-stream"},
    )
    t1 = perf_counter()

    print(
        "add_lattice_binary timings ",
        f"post={t1-t0:.3f}s ",
        f"status={response.status_code}",
    )
    response.raise_for_status()
    return response.json()



def refresh_lattice():
    url = (
        f"http://{constants.HOST_LATTICE_API}:"
        + f"{constants.PORT_COMMS}"
        + "/v1/lattice/refresh"
    )
    response = requests.post(url)
    if response.ok:
        return Lattice.model_validate(
            response.json(),
            from_attributes=True,
        )
    return None


def lattice_exists(
    facility: str,
    set_initial_conditions: str,
    magnet_filter: List[Dict[str, Any]],
    cavity_filter: List[Dict[str, Any]],
    section_filter: List[Dict[str, Any]],
    generator_filter: Dict[str, Any],
) -> bool:
    # Make GraphQL query to find_lattices
    query = """
    query FindLattices($facility: String!, $setInitialConditions: String!,  $magnetFilter: [MagnetInput!], $cavityFilter: [CavityInput!], $sectionFilter: [SectionInput!], $generatorFilter: GeneratorInput) {
        findLattices(facility: $facility, setInitialConditions: $setInitialConditions, magnetFilter: $magnetFilter, cavityFilter: $cavityFilter, sectionFilter: $sectionFilter, generatorFilter: $generatorFilter) {
            uuid
            facility
            sectionCount
        }
    }
    """
    variables = {
        "facility": facility,
        "setInitialConditions": set_initial_conditions,
        "magnetFilter": magnet_filter,
        "cavityFilter": cavity_filter,
        "sectionFilter": section_filter,
        "generatorFilter": generator_filter,
    }
    url = (
        f"http://{constants.HOST_LATTICE_API}:"
        + f"{constants.PORT_COMMS}"
        + "/graphql"
    )
    try:
        response = requests.post(
            url,
            json={"query": query, "variables": variables},
            timeout=10,
        )

        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            print(f"GraphQL error: {data['errors']}")
            return False, None

        # Check if any matching lattices found
        matching_lattices = data.get("data", {}).get("findLattices", [])
        if matching_lattices:
            # return first found lattice uuid
            return True, matching_lattices[0]["uuid"]
        else:
            print("No matching lattices found in database")
            return False, None
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to lattice API: {e}")
        return False, None


# ----------------- GET requests -----------------


def get_lattice(uuid: str = None, arrays_as_lists: bool = False) -> Lattice:
    """Fetch a lattice, preferring the binary API for array-heavy payloads.

    The default keeps arrays in the binary/numpy path longer so internal
    service callers avoid the cost of materializing large Python lists.
    """
    binary_url = (
        f"http://{constants.HOST_LATTICE_API}:"
        + f"{constants.PORT_COMMS}"
        + "/v1/lattice/binary"
    )
    if uuid:
        binary_url += f"?uuid={uuid}"

    response = requests.get(binary_url, timeout=90)
    if response.ok:
        return Lattice.from_binary(
            response.content,
            arrays_as_lists=arrays_as_lists,
        )

    # Fallback for older deployments without binary endpoint support.
    url = (
        f"http://{constants.HOST_LATTICE_API}:"
        + f"{constants.PORT_COMMS}"
        + "/v1/lattice"
    )
    if uuid:
        url += f"?uuid={uuid}"
    response = _session.get(url)
    if response.ok:
        return Lattice.model_validate(response.json(), from_attributes=True)
    return None


def get_lattice_request(request_id: str) -> Lattice | None:
    url = (
        f"http://{constants.HOST_LATTICE_API}:"
        + f"{constants.PORT_COMMS}"
        + f"/v1/lattice/request/{request_id}"
    )
    response = requests.get(url)
    if response.ok:
        return Lattice.model_validate(
            response.json(),
            from_attributes=True,
        )
    return None



def get_lattice_uuids() -> List[str]:
    url = (
        f"http://{constants.HOST_LATTICE_API}:"
        + f"{constants.PORT_COMMS}"
        + "/v1/lattice/runs"
    )
    response = requests.get(url)
    return response.json()


def get_all_screen_names() -> list:
    url = (
        f"http://{constants.HOST_LATTICE_API}:"
        + f"{constants.PORT_COMMS}"
        + "/v1/lattice/screens/names/"
    )
    response = requests.get(url)
    data = response.json()
    screen_names = [screen for screen in data]
    return screen_names


def get_all_camera_names() -> list:
    url = (
        f"http://{constants.HOST_LATTICE_API}:"
        + f"{constants.PORT_COMMS}"
        + "/v1/lattice/cameras/names/"
    )
    response = requests.get(url)
    data = response.json()
    camera_names = [camera for camera in data]
    return camera_names


def get_all_magnet_names() -> List[str]:
    url = (
        f"http://{constants.HOST_LATTICE_API}:"
        + f"{constants.PORT_COMMS}"
        + "/v1/lattice/magnets/names/"
    )
    response = requests.get(url)
    data = response.json()
    names = []
    [names.append(magnet) for magnet in data]
    return names


def get_all_bpm_names() -> List[str]:
    url = (
        f"http://{constants.HOST_LATTICE_API}:"
        + f"{constants.PORT_COMMS}"
        + "/v1/lattice/bpms/names/"
    )
    response = requests.get(url)
    data = response.json()
    names = []
    [names.append(bpm) for bpm in data]
    return names


def get_all_cavity_names() -> List[str]:
    url = (
        f"http://{constants.HOST_LATTICE_API}:"
        + f"{constants.PORT_COMMS}"
        + "/v1/lattice/cavities/names/"
    )
    response = requests.get(url)
    data = response.json()
    names = []
    [names.append(cavity) for cavity in data]
    return names


def get_all_section_names() -> List[str]:
    url = (
        f"http://{constants.HOST_LATTICE_API}:"
        + f"{constants.PORT_COMMS}"
        + "/v1/lattice/sections/names/"
    )
    response = requests.get(url)
    data = response.json()
    names = []
    [names.append(section) for section in data]
    return names


# ---------------- PATCH requests ----------------


def patch_lattice(lattice: Lattice) -> dict:
    url = (
        f"http://{constants.HOST_LATTICE_API}:"
        + f"{constants.PORT_COMMS}"
        + "/v1/lattice/"
    )
    data = lattice.model_dump()
    response = requests.patch(url, json=data)
    return response.json()


def send_prior_settings(lattice: Lattice):
    url = (
        f"http://{constants.HOST_LATTICE_API}:"
        + f"{constants.PORT_COMMS}"
        + "/v1/lattice/settings"
    )
    data = lattice.model_dump()
    response = requests.patch(url, json=data)
    return response.json()
