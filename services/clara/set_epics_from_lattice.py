from p4p.client.thread import Context
import os
from janus_common.schemas.elements import Lattice, Magnet, Generator
from janus_common.schemas.elements import Cavity as CavityElement
import CATAP.config as cfg

cfg.EPICS_TIMEOUT = 0.5
cfg.set_config_format(
    "LAURA", f"/laura-lattices/{os.environ['FACILITY']}", eager_mode=True
)
from CATAP.magnet import MagnetFactory
from CATAP.cavity import CavityFactory, Cavity
from typing import Dict
from janus_common.utils.helpers import EPICSHelper 
from janus_common.utils.constants import SIGFIG
from janus_common.utils.numeric import round_it
from janus_common.pv.translate import SectionToPV, GeneratorToPV
from scipy.interpolate import interp1d
from scipy.optimize import newton


class LatticeToEPICS:

    def __init__(self, *args, **kwargs):
        try:
            self.lattice_params = {"dipoles": ["CLA-VBC-MAG-DIP-01"]}
        except TypeError:
            self.lattice_params = {}
        self.exclude = ["CLA-S07-MAG-QUAD-11"]
        self.magnet_factory = MagnetFactory(
            is_virtual=False,
        )
        self.cavity_factory = CavityFactory(
            is_virtual=False,
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

    def initialise_all_magnets(self, lattice: Lattice) -> None:
            elements: Dict[str, Magnet] = lattice.get_elements_dict(Magnet)
            for magnet_name, epics_magnet in self.quads.items():
                magnet = elements.get(magnet_name)
                if magnet is None:
                    print(f"Could not find {magnet_name} in elements.")

                else:
                    epics_magnet.k = round_it(magnet.KnL[1], SIGFIG)
            for magnet_name, epics_magnet in self.dipoles.items():
                if "dipoles" in self.lattice_params:
                    if magnet_name in self.lattice_params["dipoles"]:
                        magnet = elements.get(magnet_name)
                        epics_magnet.k = round_it(magnet.KnL[0], SIGFIG)
                if magnet is None:
                    print(f"Could not find {magnet_name} in elements.")
            print("Magnets initialised")

    def initialise_all_sim_codes(self, lattice: Lattice) -> None:
        for section in lattice.sections.values():
            translator = SectionToPV(section)
            for m in translator.section_pv_metadata:
                value = m.get_schema_value(section)
                if value is not None:
                    self._ctx.put(m.name, value, throw=False)

    def initialise_generator(self, lattice: Lattice) -> None:
        if isinstance(lattice.generator, Generator):
            translator = GeneratorToPV(lattice.generator)
            for m in translator.generator_pv_metadata:
                value = m.get_schema_value(lattice.generator)
                if value is not None:
                    self._ctx.put(m.name, value, throw=False)

    def _convert_field_amplitude_to_power(
        self, epics_cavity: Cavity, accelerating_voltage: float
    ) -> float:
        gradient_interp = interp1d(
            epics_cavity.properties.power_calibration,
            epics_cavity.properties.gradient_calibration,
            fill_value="extrapolate",
        )

        def f(x):
            return gradient_interp(x) - accelerating_voltage

        return newton(f, accelerating_voltage)

    def initialise_all_cavities(self, lattice: Lattice) -> None:
        cavity_elems: Dict[str, CavityElement] = lattice.get_elements_dict(
            CavityElement
        )
        for name, cavity in cavity_elems.items():
            epics_cavity = self.cavity_factory.get_cavity(name)
            if epics_cavity:
                epics_cavity.set_off_crest_phase = round_it(cavity.phase, SIGFIG)
                if epics_cavity.name == "GUN":
                    # TODO: fixed gun power for now, need to change once we have calibration curves.
                    epics_cavity.set_power = 7
                    continue
            if epics_cavity and epics_cavity.properties.has_gradient_calibrations:
                power = (
                    self._convert_field_amplitude_to_power(
                        epics_cavity, cavity.field_amplitude / 1e6  # / cavity.length,
                    )
                    * 1e6
                )
                epics_cavity.set_power = round_it(power / 1e6, SIGFIG)
        print("Cavities initialised")
