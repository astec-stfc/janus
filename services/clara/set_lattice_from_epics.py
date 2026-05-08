from p4p.client.thread import Context
import os
from schemas.elements import Lattice, Magnet, InitialConditions, Generator
from schemas.elements import Cavity as CavityElement
import CATAP.config as cfg

cfg.EPICS_TIMEOUT = 0.5
cfg.set_config_format(
    "LAURA", f"/laura-lattices/{os.environ['FACILITY']}", eager_mode=True
)
from CATAP.magnet import MagnetFactory
from CATAP.cavity import CavityFactory, Cavity
from typing import Any, Dict, List, Literal, Tuple, get_origin
from math import floor, log10
from common.helpers import EPICSHelper
from common.comms_handler import (
    get_all_section_names,
)

SIGFIG = 5


def round_it(x, sig):
    if x is None:
        return 0.0
    if float(x) == 0.0:
        return 0.0
    return round(x, sig - int(floor(log10(abs(x)))) - 1)


def to_camel_case(s):
    parts = s.split("_")
    return parts[0].lower() + "".join(word.capitalize() for word in parts[1:])


class EPICSToLattice:

    def __init__(self, *args, **kwargs):
        try:
            self.lattice_params = {"dipoles": ["CLA-VBC-MAG-DIP-01"]}
        except TypeError:
            self.lattice_params = {}
        self.exclude = ["CLA-S07-MAG-QUAD-11"]
        self.facility = "CLARA"
        self.magnet_factory = MagnetFactory(
            is_virtual=True,
        )
        self.cavity_factory = CavityFactory(
            is_virtual=True,
        )
        self.quads = {
            k: v
            for k, v in self.magnet_factory.hardware.items()
            if v.properties.hardware_type == "Quadrupole"
            and v.machine_area.name
            not in ["FEA", "FEH", "FED", "C2V", "SP1", "SP2", "SP3"]
            and k not in self.exclude
        }
        self.dipoles = {
            k: v
            for k, v in self.magnet_factory.hardware.items()
            if v.properties.hardware_type == "Dipole"
            and v.machine_area.name
            not in ["FEA", "FEH", "FED", "C2V", "SP1", "SP2", "SP3"]
            and k not in self.exclude
        }
        self.cavity_aliases = {
            "GUN": "CLA-HRG1-GUN-CAV-01",
            "L01": "CLA-L01-LIN-CAV-01",
            "L02": "CLA-L02-LIN-CAV-01",
            "L03": "CLA-L03-LIN-CAV-01",
            "4HC": "CLA-L4H-LIN-CAV-01",
            "L04": "CLA-L04-LIN-CAV-01",
            "TDC1": "CLA-S07-DIA-TDC-01",
        }
        self._ctx = Context("pva")
        self.epics_helper = EPICSHelper(ctx=self._ctx)

    @property
    def tracking_status(self) -> str:
        return self.epics_helper.get_simulation_status()

    @property
    def is_tracking(self) -> bool:
        return self.tracking_status == "TRACKING"

    @property
    def tracking_mode(self) -> str:
        return self.epics_helper.get_simulation_mode()

    @property
    def is_tracking_triggered(self) -> bool:
        return self.tracking_mode == "TRIGGER"

    @property
    def is_tracking_auto(self) -> bool:
        return self.tracking_mode == "AUTO"

    @property
    def tracking_start_state(self) -> str:
        return self.epics_helper.get_simulation_start_state()

    @property
    def is_tracking_started(self) -> bool:
        return self.tracking_start_state == "ACTIVATE"

    @property
    def is_tracking_bypassed(self) -> bool:
        return self.tracking_start_state == "BYPASS"

    @tracking_start_state.setter
    def tracking_start_state(self, value: int | str) -> None:
        states = {"BYPASS": 0, "ACTIVATE": 1}
        if value in states or value in states.values():
            self.epics_helper.set_simulation_start_state(value)
        else:
            raise ValueError(
                f'Cannot set start tracking to {value}, only 0, 1, "BYPASS", or "ACTIVATE"',
            )

    def set_sim_codes_from_epics(self, lattice: Lattice) -> None:
        for section in lattice.sections.values():
            epics_sim_code = self._ctx.get(
                f"VM-{section.name}-SIMULATION:CODE", throw=False
            )
            if (
                not isinstance(epics_sim_code, TimeoutError)
                and epics_sim_code != "undefined"
            ):
                if section.model != epics_sim_code:
                    section.model = epics_sim_code

    def set_generator_from_epics(self, lattice: Lattice) -> None:
        enable_name = f"SIM-GENERATOR:ENABLE"
        epics_set_gen = self._ctx.get(enable_name, throw=False)
        if epics_set_gen:
            gen_to_set = {}
            for key, value in lattice.generator.model_dump().items():
                if key not in ["uuid", "enable"]:
                    name = f"SIM-GENERATOR:{key.upper().replace('_', '-')}"
                    epics_val = self._ctx.get(name, throw=False)
                    if isinstance(epics_val, TimeoutError):
                        print(
                            f"Could not get generator {name} from EPICS, skipping update."
                        )
                    else:
                        epics_value = self.epics_helper.epics_scalar(epics_val)
                        if (
                            get_origin(Generator.model_fields[key].annotation)
                            is Literal
                        ):
                            typ = str
                            setattr(
                                lattice.generator, key, typ(epics_value.split(" ")[-1])
                            )
                        else:
                            typ = Generator.model_fields[key].annotation
                            gen_to_set.update({key: typ(epics_value)})
                            setattr(lattice.generator, key, typ(epics_value))
            lattice.generator.enable = True

    def set_initial_conditions_from_epics(self, lattice: Lattice) -> None:
        name = f"SIM-{lattice.facility}-INITIAL-CONDITIONS:ENABLE"
        epics_init_tw = self._ctx.get(name, throw=False)
        if (
            epics_init_tw is None
            or isinstance(epics_init_tw, TimeoutError)
            or epics_init_tw == ""
        ):
            """Null conditions for initial conditions, do not update"""
            lattice.set_initial_conditions = ""
            for section in lattice.sections.values():
                section.initial_conditions = InitialConditions()
            return
        lattice.set_initial_conditions = ""
        for section in lattice.sections.values():
            if isinstance(epics_init_tw, TimeoutError):
                print(
                    f"Could not get lattice initial twiss enable from EPICS, skipping update."
                )
                continue
            if section.name in epics_init_tw.split(","):
                epics_tw = {}
                for tw in ["beta", "alpha", "nemit"]:
                    for plane in ["x", "y"]:
                        suffix = f"{tw.upper()}_{plane.upper()}"
                        name = f"SIM-{section.name}-INITIAL-CONDITIONS:{suffix}"
                        epics_tw.update(
                            {f"{tw}_{plane}": self._ctx.get(name, throw=False)}
                        )
                section.initial_conditions = None
                if len(epics_tw) != 6:
                    print(
                        f"Could not get all initial twiss for {section.name}, skipping update."
                    )
                    continue
                if any(
                    v <= 0 and k in ["beta_x", "beta_y", "nemit_x", "nemit_y"]
                    for k, v in epics_tw.items()
                ):
                    print(
                        f"{section.name} beta or nemit has non-positive value, skipping update."
                    )
                elif [isinstance(v, float) for v in epics_tw.values()]:
                    section.initial_conditions = InitialConditions(**epics_tw)
                    lattice.set_initial_conditions += f"{section.name},"
                else:
                    print(f"Could not update initial conditions for {section.name}.")
            else:
                section.initial_conditions = InitialConditions()
        if len(lattice.set_initial_conditions) > 0:
            lattice.set_initial_conditions = lattice.set_initial_conditions[:-1]

    def set_magnets_from_epics(self, elems: Dict[str, Magnet]) -> None:
        for magnet_name, epics_magnet in self.quads.items():
            magnet = elems.get(magnet_name)
            if magnet is not None:
                epics_k_value = epics_magnet.k
                if epics_k_value is not None and round_it(
                    magnet.KnL[1], SIGFIG
                ) != round_it(epics_k_value, SIGFIG):
                    print(
                        f"K1L difference for {magnet_name}: {round_it(epics_k_value, SIGFIG)} -- {round_it(magnet.KnL[1], SIGFIG)}"
                    )
                    magnet.KnL[1] = round_it(epics_k_value, SIGFIG)
        for dipole_name, epics_dipole in self.dipoles.items():
            if "dipoles" in self.lattice_params:
                if dipole_name in self.lattice_params["dipoles"]:
                    dipole = elems.get(dipole_name)
                    if dipole is not None and epics_dipole is not None:
                        epics_k_value = epics_dipole.k
                        if epics_k_value is not None and round_it(
                            dipole.KnL[0], SIGFIG
                        ) != round_it(epics_k_value, SIGFIG):
                            print(
                                f"Angle difference for {dipole_name}: {round_it(epics_k_value, SIGFIG)} -- {round_it(dipole.KnL[0], SIGFIG)}"
                            )
                            dipole.KnL[0] = round_it(epics_k_value, SIGFIG)

    def set_cavity_from_epics(
        self,
        elems: Dict[str, CavityElement],
        factory: CavityFactory,
    ) -> None:
        cavities: Dict[str, Cavity] = {name: factory.get_cavity(name) for name in elems}
        for name, cavity in elems.items():
            epics_cavity = cavities.get(name, None)
            if epics_cavity:
                # TODO Note this is related to OffCrestPhaseRead in pycatap i.e. <cavity>:getCrestPhase for clara
                if round_it(cavity.phase, SIGFIG) != round_it(
                    epics_cavity.off_crest_phase, SIGFIG
                ):
                    cavity.phase = round_it(epics_cavity.off_crest_phase, SIGFIG)
                if epics_cavity.power:
                    if "GUN" in epics_cavity.name or "HRG" in epics_cavity.name:
                        # cavity.field_amplitude = 92.5*1e6
                        continue
                    if not round_it(cavity.field_amplitude, SIGFIG - 1) == round_it(
                        epics_cavity.accelerating_voltage * 1e6, SIGFIG - 1
                    ):
                        accvol = round_it(
                            epics_cavity.accelerating_voltage * 1e6, SIGFIG - 1
                        )
                        print(f"Acc. Voltage difference for {name}")
                        print(f"Old: {cavity.field_amplitude}, New: {accvol}")
                        cavity.field_amplitude = accvol

    def set_lattice_from_epics(self, lattice: Lattice) -> Lattice:
        self.set_magnets_from_epics(
            lattice.get_elements_dict(Magnet),
        )
        self.set_cavity_from_epics(
            lattice.get_elements_dict(CavityElement),
            self.cavity_factory,
        )
        self.set_sim_codes_from_epics(lattice)
        self.set_initial_conditions_from_epics(lattice)
        self.set_generator_from_epics(lattice)
        return lattice

    @property
    def initial_condition_sections(self) -> str:
        sections_to_apply_initial_conditions = self._ctx.get(
            f"SIM-{self.facility}-INITIAL-CONDITIONS:ENABLE",
            throw=False,
        )
        if sections_to_apply_initial_conditions is not None and not isinstance(
            sections_to_apply_initial_conditions, TimeoutError
        ):
            return sections_to_apply_initial_conditions
        else:
            return ""

    def build_magnet_filters(self) -> List[Dict[str, List[float]]]:
        _filter = []
        for name, quad in self.quads.items():
            if quad.k is not None:
                _filter.append(
                    {"name": name, "KnL": [0.0, round_it(quad.k, SIGFIG), 0.0, 0.0]}
                )
        for name, dipole in self.dipoles.items():
            if "dipoles" in self.lattice_params:
                if name in self.lattice_params["dipoles"]:
                    if dipole.k is not None:
                        _filter.append(
                            {
                                "name": name,
                                "KnL": [round_it(dipole.k, SIGFIG), 0.0, 0.0, 0.0],
                            }
                        )
        return _filter

    def build_cavity_filters(self) -> List[Dict[str, float]]:
        _filter = []
        for name, cavity in self.cavity_factory.hardware.items():
            if cavity.set_off_crest_phase is not None:
                _filter.append(
                    {
                        "name": self.cavity_aliases.get(name, name),
                        "phase": round_it(cavity.set_off_crest_phase, SIGFIG),
                    }
                )
        return _filter

    def build_section_filters(self) -> List[Dict[str, Any]]:
        _filter = []
        sim_code = None
        set_initial_conditions = self.initial_condition_sections
        for section in get_all_section_names():
            epics_sim_code = self._ctx.get(f"VM-{section}-SIMULATION:CODE", throw=False)
            if (
                not isinstance(epics_sim_code, TimeoutError)
                and epics_sim_code != "undefined"
            ):
                sim_code = epics_sim_code
            initial_conditions = {}
            if set_initial_conditions:
                if section in set_initial_conditions.split(","):
                    epics_tw = {}
                    for tw in ["beta", "alpha", "nemit"]:
                        for plane in ["x", "y"]:
                            suffix = f"{tw.upper()}_{plane.upper()}"
                            name = f"SIM-{section}-INITIAL-CONDITIONS:{suffix}"
                            epics_tw.update(
                                {f"{tw}_{plane}": self._ctx.get(name, throw=False)}
                            )
                    if (
                        len(epics_tw) == 6
                        and all(isinstance(v, float) for v in epics_tw.values())
                        and not any(
                            v <= 0
                            for k, v in epics_tw.items()
                            if k in ["beta_x", "beta_y", "nemit_x", "nemit_y"]
                        )
                    ):
                        initial_conditions = {
                            to_camel_case(k): v for k, v in epics_tw.items()
                        }
            _filter.append(
                {
                    "name": section,
                    "model": sim_code,
                    "initialConditions": initial_conditions,
                }
            )
        return _filter

    def build_generator_filters(self) -> Dict[str, float | str | bool]:
        is_generator_enabled = bool(self._ctx.get("SIM-GENERATOR:ENABLE", throw=False))
        _filter = {
            "enable": (
                is_generator_enabled
                if not isinstance(
                    is_generator_enabled,
                    TimeoutError,
                )
                else False
            )
        }
        if is_generator_enabled:
            for (
                field_name,
                field_properties,
            ) in Generator.__pydantic_fields__.items():
                if field_name == "enable":
                    continue
                pv = f"SIM-GENERATOR:{field_name.upper().replace('_', '-')}"
                filter_name = to_camel_case(field_name)
                response = self._ctx.get(pv, throw=False)
                if not isinstance(response, TimeoutError):
                    value = self.epics_helper.epics_scalar(response)
                    if field_properties.annotation in [int, bool, float]:
                        _filter.update(
                            {filter_name: field_properties.annotation(value)}
                        )
                    else:
                        _filter.update({filter_name: value})
        return _filter
