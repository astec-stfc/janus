from typing import List, Dict
import requests
from common import constants
from schemas.elements import Lattice


# -------------- SEED/POST requests --------------
def add_lattice(lattice: Lattice):
    url = (
        f"http://{constants.HOST_LATTICE_API}:"
        + f"{constants.PORT_COMMS}"
        + "/v1/lattice/"
    )
    requests.post(url, json=lattice.model_dump())


def refresh_lattice():
    url = (
        f"http://{constants.HOST_LATTICE_API}:"
        + f"{constants.PORT_COMMS}"
        + "/v1/lattice/refresh"
    )
    response = requests.post(url)
    if response.status_code != 400:
        return Lattice.model_validate(
            response.json(),
            from_attributes=True,
        )
    else:
        return None


# ----------------- GET requests -----------------


def get_lattice(uuid: str = None) -> Lattice:
    url = (
        f"http://{constants.HOST_LATTICE_API}:"
        + f"{constants.PORT_COMMS}"
        + "/v1/lattice"
    )
    if uuid:
        url += f"?uuid={uuid}"
    response = requests.get(url)
    if response.status_code != 400:
        return Lattice.model_validate(
            response.json(),
            from_attributes=True,
        )
    else:
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
