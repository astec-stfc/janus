from p4p.client.thread import Context
import os
import sys
from janus_common.schemas.elements import Lattice, Magnet, Generator, PhotonMonitor
from janus_common.schemas.elements import Cavity as CavityElement
sys.path.append("/acronicta-catap/")
import catapcore.config as cfg
cfg.EPICS_TIMEOUT = 0.5
cfg.set_config_format("LAURA", f"/laura-lattices/{os.environ['FACILITY']}")
sys.path.append(f"/acronicta-catap/facility/{os.environ['FACILITY'].lower()}")

from hardware.quadrupole import QuadrupoleFactory
from hardware.photon_monitor import Photon_MonitorFactory
from hardware.dipole import DipoleFactory
from hardware.rfcavity import RFCavityFactory, RFCavity

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
            self.lattice_params = {"dipoles": ["JFEL-VBC-MAG-DIP-01"]}
        except TypeError:
            self.lattice_params = {}
        self.facility = "JFEL"
        self.exclude = ["JFEL-S07-DIA-TDC-01"]
        self.quadrupole_factory = QuadrupoleFactory(
            is_virtual=True,
        )
        self.dipole_factory = DipoleFactory(
            is_virtual=True,
        )
        self.cavity_factory = RFCavityFactory(
            is_virtual=True,
        )
        self.photon_monitor_factory = Photon_MonitorFactory(
            is_virtual=True,
        )
        self.quads = {
            k: v
            for k, v in self.quadrupole_factory.hardware.items()
            if k not in self.exclude
        }
        self.dipoles = {
            k: v
            for k, v in self.dipole_factory.hardware.items()
            if k not in self.exclude
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
                    epics_magnet.readk = round_it(magnet.KnL[1], SIGFIG)
            for magnet_name, epics_magnet in self.dipoles.items():
                magnet = None
                if "dipoles" in self.lattice_params:
                    if magnet_name in self.lattice_params["dipoles"]:
                        magnet = elements.get(magnet_name)
                        epics_magnet.readk = round_it(magnet.KnL[0], SIGFIG)
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
        self, epics_cavity: RFCavity, accelerating_voltage: float
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
            if name not in self.exclude:
                epics_cavity = self.cavity_factory.get_rfcavity(name)
                if epics_cavity:
                    epics_cavity.offcrestphaseset = round_it(cavity.phase, SIGFIG)
                    if epics_cavity.name == "GUN":
                        # TODO: fixed gun power for now, need to change once we have calibration curves.
                        epics_cavity.powermwread = 7
                        continue
            # if epics_cavity and epics_cavity.properties.has_gradient_calibrations:
            #     power = (
            #         self._convert_field_amplitude_to_power(
            #             epics_cavity, cavity.field_amplitude / 1e6  # / cavity.length,
            #         )
            #         * 1e6
            #     )
            #     epics_cavity.set_power = round_it(power / 1e6, SIGFIG)
        print("Cavities initialised")

    def initialise_all_photon_monitors(self, lattice: Lattice) -> None:
            elements: Dict[str, PhotonMonitor] = lattice.get_elements_dict(PhotonMonitor)
            for name, photon_monitor in elements.items():
                epics_photon_monitor = self.photon_monitor_factory.get_photon_monitor(name)
                if epics_photon_monitor is None:
                    print(f"Could not find {name} in elements.")
                else:
                    epics_photon_monitor.intensity = round_it(photon_monitor.intensity, SIGFIG)
            print("Photon Monitors initialised")
