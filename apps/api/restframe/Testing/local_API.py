import sys
import os
import time
import requests
import json
from typing import Union, Any


class API:
    def __init__(self, host: str = "http://127.0.0.1", port: int = 8000):
        self.baseurl = str(host) + ":" + str(port) + "/"
        self.headers = {"accept": "application/json"}

    def initialise(self, **kwargs) -> json:
        url = self.baseurl + "new"
        resp = requests.post(url, params={**kwargs}, headers=self.headers)
        json = resp.json()
        return resp.json()

    def get_settings(self) -> json:
        url = self.baseurl + "settings"
        resp = requests.get(url)
        return resp.json()

    def get_master_lattice(self) -> json:
        url = self.baseurl + "masterlattice"
        resp = requests.get(url)
        return resp.json()

    def set_ncpu(self, ncpu: str) -> json:
        url = self.baseurl + "ncpu"
        resp = requests.post(url, params={"cpu": ncpu}, headers=self.headers)
        return resp.json()

    def get_object(self, name: str, parameter: str = None) -> json:
        url = self.baseurl + "info/json"
        resp = requests.post(
            url, json={"name": name, "parameter": parameter}, headers=self.headers
        )
        return resp.json()

    def modify_object(
        self, name: str, parameter: str, value: Union[str, float, int, bool]
    ) -> json:
        url = self.baseurl + "info/json"
        # print('json', {'name': name, 'parameter': parameter, 'value': value})
        resp = requests.post(
            url,
            json={"name": name, "parameter": parameter, "value": value},
            headers=self.headers,
        )
        return resp.json()

    def track(self, end_lattice: str = "S07", **kwargs) -> json:
        url = self.baseurl + "track"
        resp = requests.post(
            url, params={"end_lattice": end_lattice, **kwargs}, headers=self.headers
        )
        return resp.json()

    def track_and_wait(self, **kwargs) -> int:
        self.track(**kwargs)
        while not self.progress["finished_tracking"]:
            print("Waiting!", self.progress)
            time.sleep(1)
        return self.progress

    @property
    def progress(self) -> json:
        url = self.baseurl + "track"
        resp = requests.get(url, headers=self.headers)
        json = resp.json()
        return json

    @property
    def tracking_finished(self) -> bool:
        url = self.baseurl + "track"
        resp = requests.get(url, headers=self.headers)
        json = resp.json()
        return float(json["progress"]) == 100 and json["finished_tracking"]

    @property
    def get_twiss(self) -> json:
        url = self.baseurl + "results/twiss"
        resp = requests.get(url)
        json = resp.json()
        return json

    @property
    def get_screens(self) -> json:
        url = self.baseurl + "results/screens"
        resp = requests.get(url)
        json = resp.json()
        return json

    def get_screen_image(self, screenname: str, force: bool = False) -> Any:
        url = self.baseurl + "results/image/" + screenname
        resp = requests.get(url, params={"force": force})
        return resp

    def get_screen_twiss(self, screenname: str) -> Any:
        url = self.baseurl + "results/twiss/" + screenname
        resp = requests.get(url)
        return resp

    @property
    def server_info(self) -> json:
        url = self.baseurl
        resp = requests.get(url)
        json = resp.json()
        return json

    def get_magnet_momenta(self) -> json:
        url = self.baseurl + "results/magnets/momentum"
        resp = requests.get(url)
        json = resp.json()
        return json
