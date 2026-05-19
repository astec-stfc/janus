import os
from copy import deepcopy
from typing import List, Dict
from pydantic import BaseModel, create_model, validator  # type: ignore
import hashlib
import json
import yaml
import sys

sys.path.append("../../")
from janus_common.schemas.elements import (
    Element,
    Screen,
    Camera,
    Lattice,
    Section,
    Magnet,
    MagnetEnum,
    BPM,
    Cavity,
    CavityEnum,
    Marker,
    Generator,
)


def save_data_json(filename, savedict):
    with open(filename, "w") as json_file:
        json.dump(savedict, json_file)


def load_data_json(filename, dataclass):
    if os.path.isfile(filename):
        with open(filename, "r") as json_file:
            dataclass.parse_file(json_file)


def save_data_yaml(filename, savedict):
    with open(filename, "w") as yaml_file:
        yaml.dump(savedict, yaml_file, default_flow_style=True)


def load_data_yaml(filename, dataclass):
    if os.path.isfile(filename):
        with open(filename, "r") as yaml_file:
            savedict = yaml.full_load(yaml_file)
            dataclass.parse_obj(savedict)


def hash_function(data):
    return hashlib.md5(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()

sf_mapping = {
    "beam_position_monitor": {"type": BPM},
    "screen": {"type": Screen, "camera": Camera},
    "marker": {"type": Marker},
    "quadrupole": {
        "type": Magnet,
        "subtype": MagnetEnum.quadrupole,
        "KnL": [None, "k1l", None, None],
        "gradient": "gradient",
    },
    "dipole": {
        "type": Magnet,
        "subtype": MagnetEnum.dipole,
        "KnL": ["angle", None, None, None],
    },
    "sextupole": {
        "type": Magnet,
        "subtype": MagnetEnum.sextupole,
        "KnL": [None, None, "k2l", None],
    },
    "corrector": {
        "type": Magnet,
        "subtype": MagnetEnum.corrector,
        "KnL": ["angle", None, None, None],
    },
    "solenoid": {
        "type": Magnet,
        "subtype": MagnetEnum.solenoid,
        "KnL": [None, None, None, None],
        "field_amplitude": None,
    },
    "rfcavity": {
        "type": Cavity,
        "subtype": CavityEnum.linac,
        "field_amplitude": None,
        # "gradient": None,
        "phase": None,
        "crest": None,
    },
    "rfdeflectingcavity": {
        "type": Cavity,
        "subtype": CavityEnum.deflecting,
        "field_amplitude": None,
        # "gradient": None,
        "phase": None,
        "crest": None,
    },
}
twiss_mapping = {"emit_x": "ex", "emit_y": "ey", "nemit_x": "enx", "nemit_y": "eny"}
centroid_values = ["x", "y"]
sigma_values = ["x", "y", "t", "cp"]
covariance_values = {
    "xx": ["x", "x"],
    "xxp": ["x", "xp"],
    "yy": ["y", "y"],
    "yyp": ["y", "yp"],
    "xy": ["x", "y"],
    "xyp": ["x", "xp"],
    "yxp": ["y", "xp"],
}
sigfig = 5


class ChangesLattice(BaseModel):
    name: str
    hash: str | None = None

    def __eq__(self, other):
        if not isinstance(other, ChangesLattice):
            return NotImplemented
        return self.hash == other.hash


class ScreenElement(BaseModel):
    screen: str
    arraydata: str | None = None
    updated: bool = False


class ScreenLattice(BaseModel):
    uuid: str | None = None
    screens: List[Screen]


def RESTData(latticeObjects_names):
    global ChangesData, ChangesClass, PrefixesClass, LatticeClass, lattice_names, lattices, PrefixData

    lattice_names = latticeObjects_names
    lattices = {lat: (ChangesLattice | None, None) for lat in lattice_names}
    ChangesDataBase = create_model(
        "ChangesData",
        uuid=(str, ...),
        prefix=(str | None, None),
        **lattices,
        hash=(str | None, None),
    )

    class ChangesData(ChangesDataBase):
        @validator("hash", always=True)
        def create_changes_hash(cls, value, values):
            # print('create_changes_hash input', cls, value, values)
            full = [
                values[lat].dict()
                for lat in lattice_names
                if lat in values and values[lat] is not None
            ]
            # print('create_changes_hash full', full)
            return hash_function(full)

        def compare_lattices(self, other):
            if not isinstance(other, ChangesData):
                return NotImplemented
            return {
                lat: getattr(self, lat) == getattr(other, lat) for lat in lattice_names
            }

        def __eq__(self, other):
            if not isinstance(other, ChangesData):
                return NotImplemented
            # print('Comparing ChangesData', self.uuid, other.uuid, self.compare_lattices(other).values(), all(self.compare_lattices(other).values()))
            return all(self.compare_lattices(other).values())

        def __neq__(self, other):
            if not isinstance(other, ChangesData):
                return NotImplemented
            return not all(self.compare_lattices(other).values())

    class ChangesClass:
        base_class = ChangesData

        def __init__(self, runs_directory):
            self._dictionary = {}
            self._runs_directory = runs_directory

        def dict(self):
            return {k: v.dict() for k, v in self._dictionary.items()}

        def json(self):
            return json.dumps({k: v.json() for k, v in self._dictionary.items()})

        def parse_obj(self, obj):
            for k, v in obj.items():
                self.add_entry(uuid=k, entry=self.base_class.parse_obj(v))

        def get_keys(self):
            return list(self._dictionary.keys())

        def get_keys_hashes(self):
            return {k: self._dictionary[k].hash for k in self._dictionary.keys()}

        def add_entry(self, uuid: str, entry: ChangesData):
            # print('ChangesClass: add_entry', uuid, changes)
            self._dictionary[uuid] = entry

        def get_uuid(self, uuid: str) -> ChangesData | None:
            return self._dictionary.get(uuid)

        def count_trues(self, true_list: list):
            true_list = (
                list(true_list) if not isinstance(true_list, list) else true_list
            )
            try:
                return true_list.index(False)
            except ValueError:
                return len(true_list)

        def run_exists(self, other: ChangesData):
            # print('ChangesClass: run_exists', self.compare_entries(other).values())
            return (
                any(self.compare_entries(other).values())
                if len(self._dictionary) > 0
                else False
            )

        def find_prefix_entry(self, other: ChangesData):
            null_result = None, lattice_names[0], 0
            if len(self._dictionary) > 0:
                lattice_matches = {}
                for uuid, change in self._dictionary.items():
                    if self.uuid_directory_exists(uuid):
                        lattice_matches[uuid] = self.count_trues(
                            change.compare_lattices(other).values()
                        )
                    else:
                        lattice_matches[uuid] = 0
                    # print('find_prefix_entry[lattice_matches]:', uuid, lattice_matches[uuid])

                most_trues = list(lattice_matches.values())
                # print('most_trues', most_trues)
                # Find where this occurs
                idx_most_trues = most_trues.index(max(most_trues))
                # print('idx_most_trues', idx_most_trues)
                # Return the lattice_exists entry with the most trues (this is ugly!?)
                result = list(list(lattice_matches.items())[idx_most_trues])
                # print('result', result)
                # Since we are in order of lattice name, we can find the starting lattice based on the length of True's
                idx_start_lattice = result[1]
                print(f"{idx_start_lattice=}")
                if idx_start_lattice < 1:
                    # If we have to re-run all lattices, return the null result
                    return null_result
                else:
                    if idx_start_lattice < len(lattice_names):
                        start_lattice = lattice_names[idx_start_lattice]
                    else:
                        start_lattice = lattice_names[-1]
                return result[0], start_lattice, idx_start_lattice
            return null_result

        def uuid_directory_exists(self, uuid: str) -> bool:
            # print('uuid_directory_exists', os.path.join(self._runs_directory, str(uuid)), os.path.isdir(os.path.join(self._runs_directory, str(uuid))))
            return os.path.isdir(os.path.join(self._runs_directory, str(uuid)))

        def compare_entries(self, other: ChangesData):
            return {
                uuid: other.hash == entry.hash and self.uuid_directory_exists(uuid)
                for uuid, entry in self._dictionary.items()
            }

        def get_entry(self, other: ChangesData) -> list | tuple | None:
            for uuid, entry in self._dictionary.items():
                if entry.hash == other.hash:
                    # print('get_entry', entry, other)
                    return uuid, entry
                    break
            return None

    prefixes = {lat: (str, None) for lat in lattice_names}
    PrefixData = create_model("PrefixData", uuid=(str, ...), **prefixes)

    class PrefixesClass(ChangesClass):
        base_class = PrefixData

        def get_prefixes(self, uuid: str) -> dict:
            prefix = self.get_uuid(uuid)
            return {lattice: getattr(prefix, lattice) for lattice in lattice_names}

        def add_entry(self, uuid: str, entry: PrefixData) -> None:  # type: ignore
            # print('PrefixesClass: add_entry', uuid, prefixes)
            for lattice in lattice_names:
                if getattr(entry, lattice) is None:
                    setattr(entry, lattice, uuid)
            self._dictionary[uuid] = entry

        def get_entry(self, settings: PrefixData) -> list | None:  # type: ignore
            for uuid, entry in self._dictionary.items():
                if entry == settings:
                    return entry
                    break

        def copy_prefixes(self, original_uuid: str, prefixIndex: int, new_uuid: str):
            # print('PrefixesClass:copy_prefixes', self.get_uuid(original_uuid))
            set2 = deepcopy(self.get_uuid(original_uuid))
            set2.uuid = new_uuid  # type: ignore
            for lattice in lattice_names[prefixIndex + 1 :]:
                setattr(set2, lattice, new_uuid)
            return set2

    lattices = {}
    for lat in lattice_names:
        if lat == "generator":
            lattices.update({lat: (Generator, ...)})
        else:
            lattices.update({lat: (Section, ...)})
    # lattices.update({'facility': (str, None)})
    LatticeData = create_model("LatticeData", **lattices)

    class LatticeClass(LatticeData):
        def set_lattice_prefix(self, lattice: str, prefix: str):
            setattr(getattr(self, lattice), "uuid", prefix)

        def get_lattice_prefix(self, lattice: str) -> str:
            return getattr(self, lattice).uuid

        def get_lattice_screens(self, lattice: str) -> List[Screen]:
            return getattr(self, lattice).screens

        def set_screen_update_flag(self, screen: str, updated: bool):
            screenElement = self.get_element(screen)
            setattr(screenElement, "updated", updated)

        def set_lattice_update_flag(self, lattice: str, updated: bool):
            # try:
            for elem in getattr(self, lattice).get_elements():
                if hasattr(elem, "updated"):
                    setattr(elem, "updated", updated)
                    if isinstance(elem, Screen):
                        setattr(elem.camera, "updated", updated)
            # except:
            #     pass

        def set_screen_array(self, lattice: str, screen_name: str, arraydata):
            setattr(getattr(self, lattice), "arraydata", arraydata)

        def get_screens(self) -> list:
            screens = []
            for lattice in lattice_names:
                try:
                    for screen in getattr(self, lattice).screens:
                        screens.append(screen.name)
                except Exception:
                    pass
            return screens

        def get_bpms(self) -> list:
            bpms = []
            for lattice in lattice_names:
                try:
                    for bpm in getattr(self, lattice).bpms:
                        bpms.append(bpm.name)
                except Exception:
                    pass
            return bpms

        def get_elements_by_type(self, elem: str) -> list:
            elems = []
            for lattice in lattice_names:
                try:
                    lat = getattr(self, lattice)
                    elems += [e.name for e in getattr(lat, elem)]
                except Exception:
                    pass
            return elems

        def get_elements_by_type_and_section(self, lattice: str, elem: str) -> list:
            elems = []
            try:
                lat = getattr(self, lattice)
                elems = getattr(lat, elem)
            except Exception:
                pass
            return elems

        def get_element(self, name: str) -> Element | dict:
            for lattice in lattice_names:
                for elem in getattr(self, lattice).get_elements():
                    if elem.name == name:
                        return elem
            return Element

        def get_elements(self) -> List:
            elems = []
            for lattice in lattice_names:
                elems += getattr(self, lattice).get_elements()
            return elems

        def get_elements_dict(self) -> Dict:
            elems = {}
            for lattice in lattice_names:
                for elem in getattr(self, lattice).get_elements():
                    elems.update({elem.name: elem})
            return elems

        def get_elements_by_section(self, uuid: str) -> Lattice:
            sections = {}
            generator = None
            for lattice in lattice_names:
                if lattice == "generator":
                    generator = getattr(self, lattice)
                else:
                    lat = getattr(self, lattice)
                    sections.update(
                        {
                            lattice: {
                                "uuid": self.get_lattice_prefix(lattice),
                                "model": lat.model,
                                "initial_conditions": lat.initial_conditions,
                            }
                        }
                    )
                    for typ in [
                        "screens",
                        "bpms",
                        "cavities",
                        "magnets",
                        "lasers",
                        "markers",
                    ]:
                        sections[lattice].update({typ: []})
                        if getattr(lat, typ):
                            for elem in getattr(lat, typ):
                                sections[lattice][typ].append(elem)
            return Lattice(
                uuid=uuid,
                sections={k: Section(name=k, **v) for k, v in sections.items()},
                generator=generator,
            )
