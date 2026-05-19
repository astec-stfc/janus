from copy import deepcopy
from io import BytesIO
from math import radians, degrees, sqrt
import os
import sys
import time
import copy
from typing import Union
import concurrent.futures
import base64
from .screen_image import ScreenImage
from .uuids import create_uuid
from . import data
from janus_common.schemas.elements import (
    Screen,
    Camera,
    CameraAnalysis,
    Lattice,
    Magnet,
    BPM,
    Cavity,
    Twiss,
    Centroid,
    Sigma,
    Covariance,
    Section,
    Marker,
    BeamSummary,
    Beam,
    Element,
    InitialConditions,
    Generator,
)
from janus_common.utils.numeric import round_it
from janus_common.utils.constants import SIGFIG

sys.path.insert(0, "/laura")
sys.path.insert(0, "/simba")
sys.path.insert(0, "/simcodes")
# import SimulationFramework.Framework as fw
# import SimulationFramework.Modules.constants as cons
# from SimulationFramework.Modules import Beams as rbf
# from SimulationFramework.Modules.Twiss import twiss
# from SimulationFramework.Framework_elements import screen as fw_screen
# from SimulationFramework.Framework_objects import chicane
import simba.Framework as fw
import simba.Modules.constants as cons
from simba.Modules import Beams as rbf
from simba.Modules.Twiss import twiss
from simba.Framework_objects import chicane, frameworkLattice
from simba.Codes.Generators import frameworkGenerator
from laura.models.element import Screen as laura_screen
from laura.models.element import RFCavity as laura_cavity
from laura.models.element import Aperture as laura_aperture

import traceback


def rest_mass_mev(particle: str = "electron") -> float:
    """return the rest mass of a particle type in MeV"""
    return (
        mass(particle)
        * cons.speed_of_light
        * cons.speed_of_light
        / cons.elementary_charge
        / 1e6
    )


def mass(particle: str = "electron") -> float:
    """return the mass of a particle type"""
    if particle.lower() == "electron":
        return cons.m_e
    elif particle.lower() == "proton":
        return cons.m_p
    else:
        raise ValueError(f"Unknown particle type: {particle}")


class SimFrame_Interface:
    """interface to SimFrame for use in the RESTFrame API"""

    def __init__(
        self,
        clean: bool = False,
        existing: bool = False,
        runs_directory: str = "./CLARA/",
        settings_file: str = "clara400_v13_combined.def",
        facility: str = "CLARA",
        master_lattice: Union[str, None] = None,
        screen_directory: Union[str, None] = None,
        particle: str = "electron",
        set_initial_conditions: str = "",
    ):
        """initialise the SimFrame interface"""
        self.verbose = True
        self.facility = facility
        self.set_initial_conditions = set_initial_conditions
        self.runs_directory = runs_directory
        self.particle = particle
        self.mass = mass(self.particle)
        self.rest_mass_mev = rest_mass_mev(self.particle)
        self._track_success = None

        self.beam_threadpool = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self.track_threadpool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.beam_threads = {}
        self.tracking_threads = {}

        self.framework = fw.Framework(
            directory=self.runs_directory,
            master_lattice=master_lattice,
            simcodes="/simcodes/SimCodes",
            generator_defaults=f"/laura-lattices/{facility}/Generators/{facility.lower()}.yaml",
            verbose=False,
            clean=False,
            eager_mode=True,
        )
        if not os.path.isfile(settings_file):
            self.settings_file = os.path.abspath(
                os.path.join(os.path.dirname(__file__), settings_file)
            )
        else:
            self.settings_file = settings_file
        self.framework.loadSettings(self.settings_file)
        self.framework.generator.number_of_particles = 4096
        for l in self.framework.lattices:
            if isinstance(self.framework[l], frameworkLattice):
                for e in self.framework[l].elementObjects.values():
                    if isinstance(e, laura_aperture):
                        self.framework[e.name].aperture.horizontal_size = 1.0
                        self.framework[e.name].aperture.vertical_size = 1.0
        self.framework.original_elementObjects = deepcopy(self.framework.elementObjects)
        self.framework.original_elementObjects["generator"] = deepcopy(
            self.framework.generator
        )
        data.RESTData(list(self.framework.latticeObjects.keys()))
        self.changeclass = data.ChangesClass(os.path.abspath(self.runs_directory))
        self.prefixesclass = data.PrefixesClass(os.path.abspath(self.runs_directory))
        self.data_structures = {
            "changes.yaml": self.changeclass,
            "prefixes.yaml": self.prefixesclass,
        }
        self.uuid = create_uuid(self.runs_directory)
        lat = self.get_lattice_elements()
        latdict = {k: v for k, v in lat.sections.items()}
        latdict.update({"generator": lat.generator})
        self.latticeclass = data.LatticeClass.model_validate(latdict)
        self.screenimage = ScreenImage(lattice_location=screen_directory)
        self.load_data_structures()

        self.changes = self.get_changes_dict()
        self.finished_tracking = False
        self.framework_directory = None
        self.tracking_history = {}
        self._current_start_section = None

    def get_uuid(self):
        return self.uuid

    def get_track_uuid(self) -> str:
        return self.track_uuid

    def reset_lattice(self):
        """reset the SimFrame lattice to it's default state"""
        self.framework.loadSettings(self.settings_file)

    def _set_null_results(self, elem: Element):
        """
        Docstring for _set_null_results

        :param self: Description
        :param elem: Description
        :type elem: Element
        """
        elem.twiss = None
        elem.sigma = None
        elem.centroid = None
        if hasattr(elem, "beam"):
            elem.beam = None
        if hasattr(elem, "camera"):
            elem.camera.sigma = None
            elem.camera.centroid = None
            elem.camera.analysis.sigma = None
            elem.camera.analysis.centroid = None
            elem.camera.analysis.covariance = None
        return

    def update_beam(self, name, elem):
        """We are using twiss at the START of the element, not the end (as is normal in Elegant)"""
        uuid = self.track_uuid
        self.basename = self.runs_directory + str(uuid) + "/" + name + ".openpmd.hdf5"
        twiss = self.get_element_twiss(name)
        if twiss is None:
            zpos = self.framework.getElement(name, "start").z
            twiss = self.get_element_twiss(zpos)
        if twiss:

            _twiss_param_mapping = {
                "ex": "emit_x",
                "ey": "emit_y",
                "enx": "nemit_x",
                "eny": "nemit_y",
            }
            elemtwiss = {}
            for parameter in list(Twiss.get_field_names(by_alias=True)):
                par = parameter
                if par in twiss.keys():
                    if par in _twiss_param_mapping.keys():
                        par = _twiss_param_mapping[par]
                        # print(f"CONVERTED TWISS PARAMETER: {parameter} to {par}")
                    elemtwiss[par] = twiss[parameter]
            # self.elemtwiss = {
            #     par: self.twiss.__getattribute__(par)
            #     for par in list(Twiss.get_field_names(by_alias=True))
            #     if par in list(self.twiss.keys())
            # }
            elem.twiss = Twiss(**elemtwiss)
            # if isinstance(elem, Marker):
            #     elem.beam = self.get_beam(elem.name)
            if hasattr(elem, "momentum"):
                elem.momentum = twiss["cp"]

            elemsigma = {
                par: twiss[f"sigma_{par}"]
                for par in list(Sigma.model_fields.keys())
                if par in data.sigma_values
            }
            elemsigma["gamma"] = twiss["sigma_cp"] / 1e6 / self.rest_mass_mev
            elem.sigma = Sigma(**elemsigma)
            elemcentroid = {
                par: twiss[f"mean_{par}"]
                for par in list(Centroid.model_fields.keys())
                if par in data.centroid_values
            }
            elemcentroid.update({"t": twiss["t"]})
            elemcentroid.update({"cp": twiss["cp"]})
            elemcentroid.update({"gamma": twiss["cp"] / 1e6 / self.rest_mass_mev})
            # self.elemcentroid.update({'q': self.elembeam.total_charge.val})
            elem.centroid = Centroid(**elemcentroid)

            if hasattr(elem, "beam") and os.path.isfile(self.basename):
                elem.beam = self.get_beam(name, force=True)
            if hasattr(elem, "camera") and isinstance(
                self.framework[name], laura_screen
            ):
                elem.camera.sigma = elem.sigma
                elem.camera.centroid = elem.centroid
                elem.camera.analysis.sigma = elem.sigma
                elem.camera.analysis.centroid = elem.centroid
                try:
                    elembeam = (
                        rbf.beam(filename=self.basename)
                        if os.path.isfile(self.basename)
                        else None
                    )
                    if elembeam:
                        elemanalysis = {
                            "xx": float(elembeam._beam.covariance("x", "x")),
                            "xxp": float(elembeam._beam.covariance("x", "xp")),
                            "yy": float(elembeam._beam.covariance("y", "y")),
                            "yyp": float(elembeam._beam.covariance("y", "yp")),
                            "xy": float(elembeam._beam.covariance("x", "y")),
                            "xyp": float(elembeam._beam.covariance("x", "yp")),
                            "yxp": float(elembeam._beam.covariance("y", "xp")),
                        }
                        elem.camera.analysis.covariance = Covariance(**elemanalysis)
                except FileNotFoundError as e:
                    print(f"Could not find file {self.basename}: {e}")

    # def update_magnet(self, elem):
    #     elem.KnL = [getattr()]

    def update_beam_and_screen(self, name, elem):
        self.update_beam(name, elem)
        if isinstance(elem, Screen):
            elem.camera.arraydata = self.get_screen_image(elem.name)
        # if isinstance(elem, Marker):
        #     elem.beam = self.get_beam(elem.name)
        elem.updated = False

    def check_section_success(self, section: Section) -> bool:
        """
        check if the tracking for a section was successful by checking if
        all of the screen hdf files were generated for that section
        """
        all_screens_exist = True
        for screen in section.screens:
            if not os.path.exists(
                self.runs_directory
                + str(section.uuid)
                + "/"
                + screen.name
                + ".openpmd.hdf5"
            ):
                print(
                    f"Screen file not found for {screen.name} in section {section.name}"
                )
                all_screens_exist = False
        return all_screens_exist

    def get_lattice(self):
        """return the master_lattice defined for the RESTFrame interface"""
        out_lattice = self.latticeclass.get_elements_by_section(self.track_uuid)
        sections = out_lattice.get_sections()
        # Filter sections to start from _current_start_section if it's set
        for section in sections:
            section_success = self.check_section_success(section)
            for name, elem in section.get_elements_dict().items():
                if section_success:
                    self.update_beam(name, elem)
                else:
                    self._set_null_results(elem)
            section.model = self.framework[section.name].code
            try:
                fw_tw = {}
                tw_set = self.framework.settings["files"][section.name]["input"][
                    "twiss"
                ]
                for tw in ["beta", "alpha", "nemit"]:
                    for plane in ["x", "y"]:
                        fw_tw.update({f"{tw}_{plane}": tw_set[f"{tw}_{plane}"]})
                section.initial_conditions = InitialConditions(**fw_tw)
            except TypeError:
                pass
            except KeyError:
                pass
        out_lattice.facility = self.facility
        if self._track_success:
            out_lattice.beam_summary = self.get_beam_summary()
        else:
            out_lattice.beam_summary = BeamSummary(
                alpha_x=[],
                alpha_y=[],
                beta_x=[],
                beta_y=[],
                energy=[],
                momentum=[],
                emittance_x=[],
                emittance_y=[],
                normalised_emittance_x=[],
                normalised_emittance_y=[],
                sigma_x=[],
                sigma_y=[],
                sigma_t=[],
                centroids_x=[],
                centroids_y=[],
                centroids_t=[],
                position=[],
            )
        out_lattice.success = self._track_success
        out_lattice.set_initial_conditions = self.set_initial_conditions
        return out_lattice

    def load_data_structures(self):
        """load YAML files for each of the data_structures elements"""
        for k, v in self.data_structures.items():
            data.load_data_yaml(self.runs_directory + k, v)

    def save_data_structures(self):
        """save YAML file of the current data_structures elements"""
        for k, v in self.data_structures.items():
            data.save_data_yaml(self.runs_directory + k, v.dict())

    def get_changes_dict(self, *args, **kwargs):
        """return a ChangesData Model with the latest lattice changes"""
        changes_lattices = {}
        for lattice in data.lattices:
            # print(f"get_changes_dict: {lattice}")
            elements = (
                list(self.framework[lattice].elements.keys())
                if lattice != "generator"
                else ["generator"]
            )
            lattice_changes = {}
            lattice_changes[lattice] = self.framework[lattice].code
            lattice_changes.update(
                self.framework.save_changes_file(
                    elements=elements,
                    dictionary=True,
                )
            )
            if lattice in self.set_initial_conditions:
                params = [
                    "beta_x",
                    "beta_y",
                    "alpha_x",
                    "alpha_y",
                    "nemit_x",
                    "nemit_y",
                ]
                init_tw = {
                    p: self.framework.settings["files"][lattice]["input"]["twiss"][p]
                    for p in params
                }
                lattice_changes.update({"initial_conditions": init_tw})
            if len(lattice_changes) > 0 and self.verbose:
                print(f"lattice_changes \t {lattice_changes}")
            if len(lattice_changes) > 0:
                changes_lattices[lattice] = data.ChangesLattice(
                    name=lattice, hash=data.hash_function(lattice_changes)
                )
        return data.ChangesData(
            uuid=self.uuid, subdirectory=self.framework.subdirectory, **changes_lattices
        )

    def set_lattice_elements(self, lattice: Lattice):
        latdict = {k: v for k, v in lattice.sections.items()}
        latdict.update({"generator": lattice.generator})
        self.latticeclass = data.LatticeClass.model_validate(latdict)
        sections = lattice.get_sections()
        groupset = []
        groupelems = []
        grouptoredo = {}
        self.set_initial_conditions = lattice.set_initial_conditions
        if lattice.generator.enable:
            for k, v in lattice.generator.model_dump().items():
                if k not in ["uuid", "enable"]:
                    if hasattr(self.framework["generator"], k):
                        setattr(self.framework["generator"], k, v)
        for sec in sections:
            if sec.name != "generator":
                for lat_elem in sec.get_elements():
                    for name, group in self.framework.groupObjects.items():
                        if (
                            lat_elem.name in group.elements
                            and isinstance(group, chicane)
                            and name not in groupset
                        ):
                            knl = round_it(radians(lat_elem.KnL[0]), SIGFIG)
                            self.framework.groupObjects[name].set_angle(knl)
                            groupset.append(name)
                            groupelems += self.framework[name].elements
                            grouptoredo = {name: knl}
                    fw_obj = self.framework[lat_elem.name]
                    if fw_obj is None:
                        continue
                    if fw_obj.name not in groupelems:
                        if fw_obj.__class__.__name__.lower() in data.sf_mapping.keys():
                            for req, par in data.sf_mapping[
                                fw_obj.__class__.__name__.lower()
                            ].items():
                                if req == "KnL":
                                    for i, val in enumerate(lat_elem.KnL):
                                        # if i == 0 and (v.objecttype in ["dipole"]):
                                        #     setattr(v, "angle", val)
                                        if i == 1 and (
                                            fw_obj.__class__.__name__.lower()
                                            == "quadrupole"
                                        ):
                                            setattr(
                                                fw_obj,
                                                "k1l",
                                                round_it(
                                                    val * fw_obj.magnetic.length,
                                                    SIGFIG,
                                                ),
                                            )
                                if (
                                    fw_obj.__class__.__name__.lower() == "quadrupole"
                                    and hasattr(lat_elem, "gradient")
                                ):
                                    setattr(
                                        fw_obj.magnetic, "gradient", lat_elem.gradient
                                    )
                                if fw_obj.__class__.__name__.lower() == "rfcavity":
                                    if req == "field_amplitude":
                                        factor = 1
                                        if (
                                            fw_obj.structure_Type == "TravellingWave"
                                            and fw_obj.n_cells > 2
                                        ):
                                            factor = 1 / float(
                                                (self.get_cells(fw_obj) + 3.8)
                                                * fw_obj.cavity.cell_length
                                                * (1 / sqrt(2))
                                            )
                                        setattr(
                                            fw_obj,
                                            req,
                                            round_it(
                                                getattr(lat_elem, req) * factor,
                                                SIGFIG,
                                            ),
                                        )
                                if req == "phase":
                                    setattr(fw_obj, req, getattr(lat_elem, req))
                if sec.name in lattice.set_initial_conditions.split(","):
                    fw_tw = {}
                    for tw in ["beta", "alpha", "nemit"]:
                        for plane in ["x", "y"]:
                            nam = f"{tw}_{plane}"
                            fw_tw.update({nam: getattr(sec.initial_conditions, nam)})
                    self.framework.settings["files"][sec.name]["input"].update(
                        {"twiss": fw_tw}
                    )
                self.framework.settings["files"][sec.name]["code"] = sec.model
                self.framework[sec.name].code = sec.model
                self.framework.change_Lattice_Code(sec.name, sec.model)
                for k, v in grouptoredo.items():
                    if isinstance(self.framework[k], chicane):
                        self.framework.groupObjects[k].set_angle(v)
            # else:
            #     self.framework.settings["generator"]["code"] = sec.model
            #     self.framework[sec.name].code = sec.model
            #     self.framework.change_generator(sec.model)
        # self.framework["CLA-L4H-LIN-CAV-01"].simulation.field_amplitude = 200

    def get_beam_summary(self):
        """set the beam summary for a section"""
        bs = BeamSummary()
        if (
            hasattr(self, "framework_directory")
            and self.framework_directory is not None
        ):
            bs.alpha_x = list(self.framework_directory.twiss.alpha_x.val)
            bs.alpha_y = list(self.framework_directory.twiss.alpha_y.val)
            bs.beta_x = list(self.framework_directory.twiss.beta_x.val)
            bs.beta_y = list(self.framework_directory.twiss.beta_y.val)
            bs.energy = list(self.framework_directory.twiss.kinetic_energy.val)
            bs.momentum = list(self.framework_directory.twiss.cp.val)
            bs.emittance_x = list(self.framework_directory.twiss.ex.val)
            bs.emittance_y = list(self.framework_directory.twiss.ey.val)
            bs.normalised_emittance_x = list(self.framework_directory.twiss.enx.val)
            bs.normalised_emittance_y = list(self.framework_directory.twiss.eny.val)
            bs.sigma_x = list(self.framework_directory.twiss.sigma_x.val)
            bs.sigma_y = list(self.framework_directory.twiss.sigma_y.val)
            bs.sigma_t = list(self.framework_directory.twiss.sigma_t.val)
            bs.centroids_x = list(self.framework_directory.twiss.mean_x.val)
            bs.centroids_y = list(self.framework_directory.twiss.mean_y.val)
            bs.centroids_t = list(self.framework_directory.twiss.t.val)
            bs.position = list(self.framework_directory.twiss.z.val)
        return bs

    def get_lattice_elements(self, lattice: Union[str, None] = None):
        if lattice is None:
            latdict = {}
            generator = None
            for lat in data.lattice_names[:]:
                lattice_elements = self.get_lattice_elements(lat)
                if isinstance(lattice_elements, dict):
                    latdict.update(
                        {
                            lat: Section(
                                name=lat,
                                screens=lattice_elements["screens"],
                                markers=lattice_elements["markers"],
                                bpms=lattice_elements["bpms"],
                                magnets=lattice_elements["magnets"],
                                cavities=lattice_elements["cavities"],
                                model=self.framework[lat].code,
                                initial_conditions=lattice_elements[
                                    "initial_conditions"
                                ],
                            )
                        }
                    )
                elif isinstance(lattice_elements, Generator):
                    generator = lattice_elements
            return Lattice(sections=latdict, generator=generator)
        else:
            # try:
            schemalattice = Section()
            latelems = []
            if (
                isinstance(self.framework[lattice], frameworkLattice)
                and self.framework[lattice].elements
            ):
                keys = self.framework[lattice].elements.keys()
                for k, v in self.framework[lattice].elements.items():
                    if v.__class__.__name__.lower() in data.sf_mapping.keys():
                        params = {"name": v.name, "length": v.physical.length}
                        sfmap = data.sf_mapping[v.__class__.__name__.lower()]
                        for req, par in sfmap.items():
                            if req == "camera":
                                params.update(
                                    {
                                        "camera": Camera(
                                            name=v.name.replace("-SCR-", "-CAM-"),
                                            analysis=CameraAnalysis(),
                                            arraydata="".encode(),
                                        )
                                    }
                                )
                            elif req == "KnL":
                                strengths = []
                                for nam in sfmap["KnL"]:
                                    if nam is not None:
                                        if v.__class__.__name__.lower() == "quadrupole":
                                            strengths.append(
                                                round_it(
                                                    getattr(v, nam) / v.magnetic.length,
                                                    SIGFIG,
                                                )
                                            )
                                            continue
                                        elif v.__class__.__name__.lower() == "dipole":
                                            strengths.append(
                                                round_it(
                                                    degrees(getattr(v, nam)),
                                                    SIGFIG,
                                                )
                                            )
                                        else:
                                            strengths.append(getattr(v, nam))
                                    else:
                                        strengths.append(0.0)
                                params.update({req: strengths})
                            elif req == "subtype":
                                params.update({req: par})
                            elif req != "type":
                                try:
                                    params.update({req: getattr(v, req)})
                                except AttributeError:
                                    params.update({req: getattr(v.magnetic, req)})
                                if (sfmap["type"] == Cavity) and (
                                    req == "field_amplitude"
                                ):
                                    if v.__class__.__name__.lower() == "rfcavity":
                                        if v.cavity.structure_Type == "TravellingWave":
                                            params["field_amplitude"] = round_it(
                                                float(
                                                    (self.get_cells(v) + 3.8)
                                                    * v.cavity.cell_length
                                                    * (1 / sqrt(2))
                                                    * v.simulation.field_amplitude
                                                ),
                                                SIGFIG,
                                            )
                                    else:
                                        params["field_amplitude"] = round_it(
                                            float(v.field_amplitude), SIGFIG
                                        )
                        for pk, pv in params.items():
                            if isinstance(pv, float):
                                if abs(pv) > 0.0:
                                    params.update({pk: round_it(pv, SIGFIG)})
                            elif isinstance(pv, list) and all(
                                isinstance(item, float) for item in pv
                            ):
                                newlist = []
                                for p in pv:
                                    if abs(p) > 0.0:
                                        newlist.append(round_it(p, SIGFIG))
                                    else:
                                        newlist.append(0.0)
                        latelems.append(sfmap["type"](**params))
                schemalattice.screens = [
                    scr for scr in latelems if isinstance(scr, Screen)
                ]
                schemalattice.markers = [
                    mar for mar in latelems if isinstance(mar, Marker)
                ]
                schemalattice.bpms = [bpm for bpm in latelems if isinstance(bpm, BPM)]
                schemalattice.cavities = [
                    cav for cav in latelems if isinstance(cav, Cavity)
                ]
                schemalattice.magnets = [
                    mag for mag in latelems if isinstance(mag, Magnet)
                ]

                schemalattice.model = self.framework[lattice].code
                schemalattice.initial_conditions = None
                if (
                    "input" in self.framework[lattice]
                    and "twiss" in self.framework[lattice]["input"]
                    and self.framework[lattice]["input"]["twiss"]
                ):
                    schemalattice.initial_conditions = InitialConditions()
                    for tw in ["beta", "alpha", "nemit"]:
                        for plane in ["x", "y"]:
                            nam = f"{tw}_{plane}"
                            setattr(
                                schemalattice.initial_conditions,
                                nam,
                                self.framework[lattice]["input"]["twiss"][nam],
                            )
                return {
                    "screens": schemalattice.screens,
                    "markers": schemalattice.markers,
                    "magnets": schemalattice.magnets,
                    "bpms": schemalattice.bpms,
                    "cavities": schemalattice.cavities,
                    "model": schemalattice.model,
                    "initial_conditions": schemalattice.initial_conditions,
                }
            elif isinstance(self.framework[lattice], frameworkGenerator):
                gendict = {}
                for k in Generator.model_fields:
                    if k not in ["uuid", "enable"]:
                        gendict.update({k: getattr(self.framework[lattice], k)})
                return Generator(**gendict)
            return {
                "screens": None,
                "magnets": None,
                "bpms": None,
                "cavities": None,
                "markers": None,
                "beam_summary": None,
                "model": "",
                "initial_conditions": None,
            }

    def get_screen_names(self, lattice: Union[str, None] = None):
        if lattice is None:
            return {
                lattice: Section(screens=self.get_screen_names(lattice))
                for lattice in data.lattice_names[:]
            }
        else:
            try:
                screens = self.framework[lattice].getElementType("screen", "name")
                return [
                    Screen(
                        name=scr,
                        camera=Camera(
                            name=scr.replace("-SCR-", "-CAM-"),
                            analysis=CameraAnalysis(),
                        ),
                    )
                    for scr in screens
                    if "-SCR-" in scr
                ]
            except Exception:
                return []

    def set_parallel_cpu_number(self, ncpu: int = 1) -> dict:
        """set the no. of cpu's to use and return as a dict"""
        self.framework.executables.define_astra_command(ncpu=ncpu)
        self.framework.executables.define_elegant_command(ncpu=ncpu)
        return {"ncpu": ncpu}

    def put_object_properties(
        self, object: str, parameter: str, value: Union[int, float, str, None] = None
    ) -> dict:
        """return a dict of the current object properties"""
        d = {}
        try:
            original_value = getattr(self.framework[object], parameter)
        except Exception:
            original_value = None
        d["parameter"] = parameter
        if value is not None:
            d["set_value"] = value
            setattr(self.framework[object], parameter, value)
            d["original_value"] = original_value
        d["value"] = getattr(self.framework[object], parameter)
        return d

    def get_settings_filename(self) -> dict:
        """return a dict of the current settings filename"""
        return {"settings": self.framework.settingsFilename}

    def track(self, frameworkcopy, uuid, endfile: Union[str, None] = "S07"):
        """perform a SimFrame tracking run"""
        self._track_success = None
        if self.verbose:
            print("track")
        self.finished_tracking = False
        changes_dict = self.get_changes_dict()
        if self.verbose:
            print("changes_dict", changes_dict)
        # Check if the settings already exist in a run, if not track else re-load existing directory
        if not changes_dict == self.changeclass.get_uuid(uuid):
            startfile = data.lattice_names[-1]
            if self.verbose:
                print("TRACKING: Something has changed")
            if self.verbose:
                print(
                    "TRACKING: Already exists?",
                    self.changeclass.run_exists(changes_dict),
                )
            if not self.changeclass.run_exists(changes_dict):
                if self.verbose:
                    print("TRACKING: Need to track")
                uuid = self.uuid = create_uuid(self.runs_directory)
                if self.verbose:
                    print("TRACKING: uuid = ", uuid)
                frameworkcopy.setSubDirectory(self.runs_directory + str(uuid))
                prefix, startfile, startfile_index = self.changeclass.find_prefix_entry(
                    changes_dict
                )
                if self.verbose:
                    print("TRACKING: prefix 1 = ", prefix, startfile)
                startfile = startfile if startfile_index > 0 else "generator"
                if prefix is not None:
                    lattice_prefix = self.prefixesclass.get_prefixes(prefix)[startfile]
                    frameworkcopy.set_lattice_prefix(
                        startfile, "../" + str(lattice_prefix) + "/"
                    )
                    self.prefixesclass.add_entry(
                        uuid,
                        self.prefixesclass.copy_prefixes(prefix, startfile_index, uuid),
                    )
                    if self.verbose:
                        print(
                            "TRACKING: prefix = ",
                            prefix,
                            lattice_prefix,
                            startfile,
                            frameworkcopy[startfile].prefix,
                        )
                else:
                    if self.verbose:
                        print("TRACKING: prefix is None")
                    self.prefixesclass.add_entry(uuid, data.PrefixData(uuid=uuid))
                frameworkcopy.save_changes_file(
                    filename=frameworkcopy.subdirectory + "/changes.yaml"
                )
                try:
                    self._current_start_section = startfile
                    for f in frameworkcopy.latticeObjects.keys():
                        frameworkcopy[f].global_parameters["master_subdir"] = (
                            self.runs_directory + str(uuid)
                        )
                        if hasattr(frameworkcopy[f], "headers"):
                            for h in frameworkcopy[f].headers:
                                frameworkcopy[f].headers[h].global_parameters[
                                    "master_subdir"
                                ] = self.runs_directory + str(uuid)
                    frameworkcopy.track(startfile=startfile, endfile=endfile)
                except Exception as e:
                    print("TRACKING: Problem during tracking!")
                    print(e)
                    # tracking failed, so no success
                    self._track_success = False
                self.changeclass.add_entry(uuid, changes_dict)
                self.framework.progress = 100
                self.tracking_finished = True
            else:
                uuid, entry = self.changeclass.get_entry(changes_dict)
                self.uuid = uuid
                if self.verbose:
                    print("TRACKING: Tracking run exists!", uuid)
                frameworkcopy.setSubDirectory(self.runs_directory + str(uuid))
                if self.tracking_history.get(uuid) is not None:
                    self._track_success = self.tracking_history[uuid]
                prefix, startfile, startfile_index = self.changeclass.find_prefix_entry(
                    changes_dict
                )
                self._current_start_section = (
                    startfile if startfile_index > 0 else "generator"
                )
                self.framework.progress = 100
                self.tracking_finished = True
            try:
                # this will raise a FileNotFoundError if the tracking failed
                # to generate the beam files after a certain element
                self.framework_directory = fw.frameworkDirectory(
                    twiss=True,
                    beams=True,
                    framework=frameworkcopy,
                    rest_mass=self.mass,
                    E0=mass(self.particle),
                )
            except FileNotFoundError as e:
                print(e)
                self._track_success = False
                self.tracking_finished = True
            except Exception as e:
                print("TRACKING: Problem loading framework directory!")
                print(e)
                traceback.print_exc()
                self._track_success = False
                self.tracking_finished = True
            # print(self.framework_directory.twiss.keys())
            self.track_uuid = uuid
            self.track_startfile = startfile
            self.set_lattice_update_flag(uuid, startfile)
        else:
            if self.verbose:
                print("TRACKING: NOTHING has changed!!")
            pass
        try:
            start = time.time()
            self.save_data_structures()
            if self.verbose:
                print("Saving data structures", time.time() - start)
            self.load_data_structures()
            if self.verbose:
                print("Re-loading data structures", time.time() - start)
            self.set_lattice_update_flag(uuid, "generator", force=True)
            if self.tracking_history.get(uuid) is not None:
                # This track may have failed before
                # so we check the tracking history
                # to avoid trying to load data from a failed track
                self._track_success = self.tracking_history[uuid]
            self.tracking_finished = True
        except Exception as e:
            print(e)
            print("Problem with saving data structures!")
            self._track_success = False
            self.tracking_finished = True
        # if tracking_success hasn't been set, then it must have worked!
        if self._track_success is None:
            self._track_success = True
        self.tracking_history.update({uuid: self._track_success})
        self.finished_tracking = True
        print(f"Tracking worked up to: {self._current_start_section}")

    def set_lattice_update_flag(
        self, trackuuid: str, current_start_lattice: str, force: bool = False
    ):
        """determine if the screen data has changed and update entries in the latticeclass model"""
        for lattice, uuid in list(self.prefixesclass.get_prefixes(trackuuid).items()):
            uuid = uuid if uuid is not None else trackuuid
            if (
                force
                or current_start_lattice == lattice
                or self.latticeclass.get_lattice_prefix(lattice) != uuid
            ):
                if current_start_lattice == lattice:
                    uuid = trackuuid
                if self.verbose:
                    print(lattice, "uuid changed", uuid)
                self.latticeclass.set_lattice_prefix(lattice, uuid)
                self.latticeclass.set_lattice_update_flag(lattice, True)
            else:
                self.latticeclass.set_lattice_update_flag(lattice, False)
                # if self.verbose:
                #     print(lattice, "uuid hasn't changed")
                pass

    def assign_screen_data(self, uuid: str, screen: Screen) -> BytesIO:
        """assign screen array data to the ScreenData model"""
        screen_basename = self.runs_directory + str(uuid) + "/" + screen.name
        if not os.path.isfile(screen_basename + ".png"):
            screenbeam = rbf.beam(filename=screen_basename + ".openpmd.hdf5")
            scrimg, ardat = self.screenimage.get_screen_array(screen.name, screenbeam)
            scrimg.save(screen_basename + ".png", format="png")
        else:
            ardat = self.screenimage.load_image(screen_basename + ".png")
        # seek to the start of the bytes before returning
        ardat.seek(0)
        return ardat

    def start_tracking(
        self, endfile: Union[str, None] = "S07", rerun: str = False
    ) -> dict:
        """start tracking run and return progress dict"""
        self.finished_tracking = False
        self.framework.progress = 0
        frameworkcopy = copy.deepcopy(self.framework)
        self.track(frameworkcopy, self.uuid, endfile=endfile)
        # we wait in self.track, so if that exits then we must have
        # finished tracking. Successfully or not.
        self.finished_tracking = True
        return self.get_tracking_status()

    def get_tracking_status(self) -> dict:
        """return progress of tracking run as dict"""
        status_dict = {}
        status_dict.update(
            {
                "progress": float(self.framework.progress),
                "finished_tracking": self.finished_tracking,
            }
        )
        if self.finished_tracking:
            status_dict.update({"momentum": self.get_magnet_momentum()})
        return status_dict

    def get_screens(self) -> dict:
        """return list of screen names"""
        return {"screens": self.latticeclass.get_screens()}

    def get_bpms(self) -> dict:
        """return list of bpm names"""
        return {"bpms": self.latticeclass.get_bpms()}

    def get_elements_by_type(self, elem: str) -> dict:
        """return list of element names by type"""
        return {elem: self.latticeclass.get_elements_by_type(elem)}

    def get_beam(self, marker: str, force: bool = False) -> Beam | None:
        """return screen image as bytes array"""
        marker_dict = self.latticeclass.get_element(marker)
        uuid = self.track_uuid
        if type(marker_dict) in [Marker, Screen] and (marker_dict.updated or force):
            basename = self.runs_directory + str(uuid) + "/" + marker_dict.name
            beam = rbf.beam(filename=basename + ".openpmd.hdf5")
            # self.latticeclass.set_screen_update_flag(screen, False)
            beam_obj = Beam()
            beam_obj.x = list(beam.x.val)
            beam_obj.y = list(beam.y.val)
            beam_obj.z = list(beam.z.val)
            beam_obj.cpx = list(beam.cpx.val)
            beam_obj.cpy = list(beam.cpy.val)
            beam_obj.cpz = list(beam.cpz.val)
            return beam_obj
        return None

    def get_screen_image(self, screen: str, force: bool = False) -> bytes:
        """return screen image as bytes array"""
        screen_dict = self.latticeclass.get_element(screen)
        if isinstance(screen_dict, Screen) and (screen_dict.updated or force):
            self.arraydata = self.assign_screen_data(self.track_uuid, screen_dict)
            # self.latticeclass.set_screen_update_flag(screen, False)
            return base64.b64encode(self.arraydata.read())
        return "".encode()

    def get_element_twiss(self, elem: str | float | int) -> twiss | None:
        """return twiss parameters at element"""
        if self.framework_directory is not None:
            try:
                if isinstance(elem, str):
                    return self.framework_directory.twiss.get_twiss_at_element(
                        elem, before=True
                    )
                else:
                    return self.framework_directory.twiss.get_twiss_at_z(elem)

            except Exception as e:
                print(e, elem)
                return None
        else:
            return None

    def get_magnet_momentum(self) -> dict:
        """return dictionary of magnets and the beam energies at each magnet"""
        if self.framework_directory is not None:
            names = self.framework_directory.twiss.element_name.val
            momentum = self.framework_directory.twiss.cp.val
            magnets = filter(
                lambda x: (
                    "-MAG-" in x[0] or "-SCR-" in x[0]
                    if isinstance(x[0], str)
                    else False
                ),
                zip(names, momentum),
            )
            return dict(magnets)
        else:
            return {}

    def get_rmatrix(self, start_element: str, end_element: str) -> dict:
        """return rmatrix between two points"""
        pass

    def get_cells(self, cav: laura_cavity) -> int:
        """
        Get the number of cavity cells.

        Returns
        -------
        int or None
            The number of cavity cells, or None if not defined.
        """
        if (
            cav.cavity.n_cells == 0 or cav.cavity.n_cells is None
        ) and cav.cavity.cell_length > 0:
            cells = round(
                (cav.physical.length - cav.cavity.cell_length) / cav.cavity.cell_length
            )
            cells = int(cells - (cells % 3))
        elif cav.cavity.n_cells:
            if cav.cavity.cell_length == cav.physical.length:
                cells = 1
            else:
                cells = int(cav.cavity.n_cells - (cav.cavity.n_cells % 3))
        else:
            cells = 0
        return cells
