import time
import requests
from typing import Any, Union, Tuple, Dict
from common import constants
from schemas.elements import Lattice


class API:
    # MIGHT NEED TO CHANGE URL HERE, IF CONTAINER IS ON HOST THIS IS OKAY,
    # OTHERWISE MIGHT NEED DOCKER-NAME.
    def __init__(
        self,
        host: str = f"http://{constants.HOST_WEB_RESTFRAME}",
        port: int = constants.PORT_RESTFRAME,
    ):
        self.baseurl = f"{host}:{port}/"
        self.headers = {"accept": "application/json"}

    def initialise(self, **kwargs):
        url = self.baseurl + "new"
        resp = requests.post(url, params={**kwargs}, headers=self.headers)
        return resp.json()

    def get_settings(self):
        url = self.baseurl + "settings"
        resp = requests.get(url)
        return resp.json()

    def get_master_lattice(self):
        url = self.baseurl + "masterlattice"
        resp = requests.get(url)
        return resp.json()

    def get_lattice(self) -> Lattice:
        url = self.baseurl + "lattice"
        resp = requests.get(url)
        return Lattice.model_validate(
            resp.json(),
            from_attributes=True,
        )

    def get_latest_run_uuid(self) -> str:
        url = self.baseurl + "uuid"
        resp = requests.get(url)
        return resp.json()["uuid"]

    def set_ncpu(self, ncpu: str):
        url = self.baseurl + "ncpu"
        resp = requests.post(url, params={"cpu": ncpu}, headers=self.headers)
        return resp.json()

    def get_object(self, name: str, parameter: str = None):
        url = self.baseurl + "info/json"
        resp = requests.post(
            url,
            json={"name": name, "parameter": parameter},
            headers=self.headers,
        )
        return resp.json()

    def modify_lattice(self, lattice: Lattice):
        url = self.baseurl + "lattice"
        # print('json', {'name': name, 'parameter': parameter, 'value': value})
        resp = requests.post(
            url,
            json=lattice.model_dump(),
            headers=self.headers,
        )
        return resp.json()

    def modify_object(
        self, name: str, parameter: str, value: Union[str, float, int, bool]
    ):
        url = self.baseurl + "info/json"
        # print('json', {'name': name, 'parameter': parameter, 'value': value})
        resp = requests.post(
            url,
            json={"name": name, "parameter": parameter, "value": value},
            headers=self.headers,
        )
        return resp.json()

    def track(self, end_lattice: str = "S07", **kwargs):
        url = self.baseurl + "track"
        resp = requests.post(
            url,
            params={"end_lattice": end_lattice, **kwargs},
            headers=self.headers,
        )
        return resp.json()

    def track_and_wait(self, **kwargs):
        self.track(**kwargs)
        while not self.progress["finished_tracking"]:
            print("Waiting!", self.progress)
            time.sleep(1)

    @property
    def progress(self):
        url = self.baseurl + "track"
        resp = requests.get(url, headers=self.headers)
        json = resp.json()
        return json

    @property
    def finished_tracking(self):
        url = self.baseurl + "track"
        resp = requests.get(
            url,
            headers=self.headers,
        )
        json = resp.json()
        return json["finished_tracking"]

    @property
    def momentum(self):
        url = self.baseurl + "results/magnets/momentum"
        resp = requests.get(url)
        json = resp.json()
        return json

    @property
    def get_twiss(self):
        url = self.baseurl + "results/twiss"
        resp = requests.get(url)
        json = resp.json()
        return json

    @property
    def get_screens(self):
        url = self.baseurl + "results/screens"
        resp = requests.get(url)
        json = resp.json()
        return json

    @property
    def get_bpms(self):
        url = self.baseurl + "results/bpms"
        resp = requests.get(url)
        json = resp.json()
        return json

    def get_screen(self, screenname: str) -> Tuple[int, Dict[str, Any]]:
        url = self.baseurl + "results/image/" + screenname
        resp = requests.get(url)
        return resp.status_code, resp.content

    def get_bpm(self, bpmname: str) -> Tuple[int, Dict[str, Any]]:
        url = self.baseurl + "results/bpms/" + bpmname
        resp = requests.get(url)
        return resp.status_code, resp.json()

    @property
    def server_info(self):
        url = self.baseurl
        resp = requests.get(url)
        json = resp.json()
        return json
