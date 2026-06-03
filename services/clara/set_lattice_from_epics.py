from p4p.client.thread import Context
import os
from janus_common.schemas.elements import (
    Lattice,
    Magnet,
    SimulationState,
    SimulationMode,
    SimulationTrigger,
)
from janus_common.schemas.elements import Cavity as CavityElement
import CATAP.config as cfg

cfg.EPICS_TIMEOUT = 0.5
cfg.set_config_format(
    "LAURA", f"/laura-lattices/{os.environ['FACILITY']}", eager_mode=True
)
from CATAP.magnet import MagnetFactory
from CATAP.cavity import CavityFactory, Cavity
from typing import Any, Dict, List
from janus_common.utils.helpers import EPICSHelper, to_camel_case
from janus_common.utils.numeric import round_it
from janus_common.pv.translate import SectionToPV, GeneratorToPV, SimulationToPV, LatticeToPV
from janus_common.utils.constants import SIGFIG

VIRTUAL_MODE = eval(os.getenv("VIRTUAL_MODE"))

class EPICSToLattice:

    def __init__(self, *args, **kwargs):
        try:
            self.lattice_params = {"dipoles": ["CLA-VBC-MAG-DIP-01"]}
        except TypeError:
            self.lattice_params = {}
        self.exclude = ["CLA-S07-MAG-QUAD-11"]
        self.facility = "CLARA"
        self.magnet_factory = MagnetFactory(
            is_virtual=VIRTUAL_MODE,
        )
        self.cavity_factory = CavityFactory(
            is_virtual=VIRTUAL_MODE,
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
        self.simulation_translator = SimulationToPV()
        self.lattice_translator = LatticeToPV()
        self.epics_helper = EPICSHelper(ctx=self._ctx)

    @property
    def tracking_status(self) -> str:
        return self.epics_helper.get_pv(self.simulation_translator.status_pv.name)

    @property
    def is_tracking(self) -> bool:
        return self.tracking_status == SimulationState.TRACKING.value

    @property
    def tracking_mode(self) -> str:
        return self.epics_helper.get_pv(self.simulation_translator.mode_pv.name)

    @property
    def is_tracking_triggered(self) -> bool:
        return self.tracking_mode == SimulationMode.TRIGGER.value

    @property
    def is_tracking_auto(self) -> bool:
        return self.tracking_mode == SimulationMode.AUTO.value

    @property
    def tracking_start_state(self) -> str:
        return self.epics_helper.get_pv(self.simulation_translator.start_pv.name)

    @property
    def is_tracking_started(self) -> bool:
        return self.tracking_start_state == SimulationTrigger.ACTIVATE.value

    @property
    def is_tracking_bypassed(self) -> bool:
        return self.tracking_start_state == SimulationTrigger.BYPASS.value

    @tracking_start_state.setter
    def tracking_start_state(self, value: int | str) -> None:
        enum_names = {name: member for name, member in SimulationTrigger.__members__.items()}
        enum_values = {member.value for member in SimulationTrigger}

        if value in enum_values:
            self.epics_helper.put_pv(self.simulation_translator.start_pv.name, value)
            return

        if isinstance(value, str) and value.upper() in enum_names:
            self.epics_helper.put_pv(self.simulation_translator.start_pv.name, enum_names[value.upper()].value)
            return

        valid_names = ", ".join(enum_names)
        valid_values = ", ".join(str(v) for v in sorted(enum_values))
        raise ValueError(
            f'Cannot set start tracking to {value}. Valid names are {valid_names} or values {valid_values}.',
        )

    def set_section_from_epics(self, lattice: Lattice) -> None:
        for section in lattice.sections.values():
            translator = SectionToPV(section)
            pv_metadata = translator.section_pv_metadata
            for m in pv_metadata:
                epics_result = self.epics_helper.epics_scalar(
                    self._ctx.get(m.name, throw=False)
                )
                if (
                    not isinstance(epics_result, TimeoutError)
                    and epics_result != "undefined"
                ):
                    current_value = m.get_schema_value(section)
                    if current_value != epics_result:
                        m.set_schema_value(section, epics_result)

    def set_generator_from_epics(self, lattice: Lattice) -> None:
        generator = lattice.generator
        if generator is None:
            return
        translator = GeneratorToPV()
        for m in translator.generator_pv_metadata:
            epics_result = self.epics_helper.epics_scalar(
                self._ctx.get(m.name, throw=False)
            )
            if (
                not isinstance(epics_result, TimeoutError)
                and epics_result != "undefined"
            ):
                current_value = m.get_schema_value(generator)
                if current_value != epics_result:
                    m.set_schema_value(generator, epics_result)

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

    def set_apply_initial_condtions_from_epics(self, lattice: Lattice) -> None:
        lattice.set_initial_conditions = self.initial_condition_sections

    def set_lattice_from_epics(self, lattice: Lattice) -> Lattice:
        self.set_apply_initial_condtions_from_epics(lattice)
        self.set_magnets_from_epics(
            lattice.get_elements_dict(Magnet),
        )
        self.set_cavity_from_epics(
            lattice.get_elements_dict(CavityElement),
            self.cavity_factory,
        )
        self.set_section_from_epics(lattice)
        # self.set_initial_conditions_from_epics(lattice)
        self.set_generator_from_epics(lattice)
        return lattice

    @property
    def initial_condition_sections(self) -> str:
        sections_to_apply_initial_conditions = self._ctx.get(
            self.lattice_translator.apply_initial_conditions_pv_metadata.name,
            throw=False,
        )
        if sections_to_apply_initial_conditions is None or isinstance(
            sections_to_apply_initial_conditions, TimeoutError
        ):
            return ""
        value = self.epics_helper.epics_scalar(sections_to_apply_initial_conditions)
        return value if isinstance(value, str) else str(value)

    def build_magnet_filters(self, lattice: Lattice) -> List[Dict[str, List[float]]]:
        _filter = []
        for name, magnet in lattice.get_elements_dict(Magnet).items():
            if isinstance(magnet, Magnet) and (
                name in self.quads or name in self.lattice_params.get("dipoles", [])
            ):
                if magnet.KnL is not None:
                    _filter.append(
                        {
                            "name": name,
                            "KnL": [
                                round_it(magnet.KnL[0], SIGFIG),
                                round_it(magnet.KnL[1], SIGFIG),
                                round_it(magnet.KnL[2], SIGFIG),
                                round_it(magnet.KnL[3], SIGFIG),
                            ],
                        }
                    )
        return _filter

    def build_cavity_filters(self, lattice: Lattice) -> List[Dict[str, float]]:
        _filter = []
        _keywords = ["phase", "field_amplitude"]
        for name, cavity in lattice.get_elements_dict(CavityElement).items():
            _cavity_filter = {"name": name}
            _cavity_filter.update(
                {
                    to_camel_case(k): round_it(getattr(cavity, k), SIGFIG)
                    for k in _keywords
                }
            )
            _filter.append(_cavity_filter)
        return _filter

    def build_section_filters(self, lattice: Lattice) -> List[Dict[str, Any]]:
        _filter = []
        sim_code = None
        set_initial_conditions = (
            lattice.set_initial_conditions if lattice.set_initial_conditions else ""
        )
        for section in lattice.get_sections():
            _filter.append(
                {
                    "name": section.name,
                    "model": section.model,
                    "initialConditions": (
                        {
                            to_camel_case(k): v
                            for k, v in section.initial_conditions.model_dump().items()
                        }
                        if section.initial_conditions and section.name in set_initial_conditions
                        else None
                    ),
                }
            )
        return _filter

    def build_generator_filters(
        self, lattice: Lattice
    ) -> Dict[str, float | str | bool]:
        _filter = {}
        if lattice.generator is None:
            return None
        if not lattice.generator.enable:
            return None
        _filter.update(
            {
                to_camel_case(k): v
                for k, v in lattice.generator.model_dump().items()
                if k not in ["uuid"]
            }
        )
        return _filter
