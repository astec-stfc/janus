from typing import Any, List, Dict
import requests
from janus_common.utils import constants
from janus_common.schemas.elements import Lattice

_session = requests.Session()


# -------------- SEED/POST requests --------------
def add_lattice(lattice: Lattice, request_id: str = None):
    url = (
        f"http://{constants.HOST_LATTICE_API}:"
        + f"{constants.PORT_COMMS}"
        + "/v1/lattice/"
    )
    params = (
        {"request_id": request_id} if request_id else None
    )  # when lattice is added via integrated model loop (client-triggered)
    response = requests.post(url, json=lattice.model_dump(), params=params)
    response.raise_for_status()



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


def get_lattice(uuid: str = None) -> Lattice:
    url = (
        f"http://{constants.HOST_LATTICE_API}:"
        + f"{constants.PORT_COMMS}"
        + "/v1/lattice"
    )
    if uuid:
        url += f"?uuid={uuid}"
    response = _session.get(url)
    if response.ok:
        return Lattice.model_validate(
            response.json(),
            from_attributes=True,
        )
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
