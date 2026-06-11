import time
import os
from typing import Any, Dict
from p4p.server import Server
from janus_common.schemas import elements
from p4p.server.thread import SharedPV
from janus_common.pv.builder import Builder
from janus_common.pv.translate import (
    ElementToPV,
    GeneratorToPV,
    SectionToPV,
    SimulationToPV,
    LatticeToPV,
)
from janus_common.utils.comms_handler import get_lattice

PV_OUTPUT_DIR = "./output"


def get_server_conf():
    server_port = str(os.getenv("EPICS_PVAS_SERVER_PORT", 6090))
    client_port = str(os.getenv("EPICS_PVA_SERVER_PORT", 6090))
    broadcast_port = str(os.getenv("EPICS_PVAS_BROADCAST_PORT", 6090))
    auto_addr_list = str(os.getenv("EPICS_PVA_AUTO_ADDR_LIST", "NO"))
    addr_list = str(os.getenv("EPICS_PVA_ADDR_LIST", ""))
    interface_addr_list = str(os.getenv("EPICS_PVA_INTF_ADDR_LIST", ""))
    conf = {
        "EPICS_PVAS_BROADCAST_PORT": broadcast_port,
        "EPICS_PVAS_SERVER_PORT": server_port,
        "EPICS_PVA_ADDR_LIST": addr_list,
        "EPICS_PVA_AUTO_ADDR_LIST": auto_addr_list,
        "EPICS_PVA_SERVER_PORT": client_port,
        "EPICS_PVA_INTF_ADDR_LIST": interface_addr_list,
    }
    return conf


def _write_facility_pv_yaml(
    facility: str,
    pvs: Dict[str, Any],
):
    """
    Utility function to write the PVs being served to a yaml file.
    """
    import yaml

    if not os.path.exists(PV_OUTPUT_DIR):
        os.makedirs(PV_OUTPUT_DIR)
    if not os.path.exists(os.path.join(PV_OUTPUT_DIR, facility)):
        os.makedirs(os.path.join(PV_OUTPUT_DIR, facility))
    with open(
        f"{os.path.join(PV_OUTPUT_DIR, facility, 'pvs.yaml')}",
        "w",
    ) as f:
        print(f"Writing {os.path.join(PV_OUTPUT_DIR, facility, f'pvs.yaml')}: {len(pvs)}")
        output = {facility: pvs}
        yaml.dump(output, f)


def construct_pvs_from_lattice(lattice: elements.Lattice) -> Dict[
    str,
    SharedPV,
]:
    """
    Converts fields for each element into SharedPVs,
    non-native types are deconstructed into native types
    """
    pv_builder = Builder()
    shared_pvs = {}
    output = {}
    for element in lattice.get_elements():
        element_translator = ElementToPV(element=element)
        shared_pvs.update(
            {
                pv: pv_builder.make_shared_pv_from_type(pv_type)
                for pv, pv_type in element_translator.element_pv_types.items()
            }
        )
        output.update(
            {
                pv: {"type": str(pv_type)}
                for pv, pv_type in element_translator.element_pv_types.items()
            }
        )
    generator_translator = GeneratorToPV()
    shared_pvs.update(
        {
            pv: pv_builder.make_shared_pv_from_type(pv_type)
            for pv, pv_type in generator_translator.generator_pv_types.items()
        }
    )
    output.update(
        {
            pv: {"type": str(pv_type)}
            for pv, pv_type in generator_translator.generator_pv_types.items()
        }
    )
    for section in lattice.get_sections():
        section_translator = SectionToPV(section.name)
        shared_pvs.update(
            {
                pv: pv_builder.make_shared_pv_from_type(pv_type)
                for pv, pv_type in section_translator.section_pv_types.items()
            }
        )
        output.update(
            {
                pv: {"type": str(pv_type)}
                for pv, pv_type in section_translator.section_pv_types.items()
            }
        )
    lattice_translator = LatticeToPV()
    shared_pvs.update(
        {
            pv: pv_builder.make_shared_pv_from_type(pv_type)
            for pv, pv_type in lattice_translator.lattice_pv_types.items()
        }
    )
    output.update(
        {
            pv: {"type": str(pv_type)}
            for pv, pv_type in lattice_translator.lattice_pv_types.items()
        }
    )
    simulation_translator = SimulationToPV()
    shared_pvs.update(
        {
            pv: pv_builder.make_shared_pv_from_type(pv_type)
            for pv, pv_type in simulation_translator.simulation_pv_types.items()
        }
    )
    output.update(
        {
            pv: {"type": str(pv_type)}
            for pv, pv_type in simulation_translator.simulation_pv_types.items()
        }
    )
    seed_pv = f"{lattice.facility}:SIM:SEED"
    shared_pvs[seed_pv] = pv_builder.make_shared_pv_from_type(int)
    output[seed_pv] = {"type": str(int)}
    _write_facility_pv_yaml(facility=lattice.facility, pvs=output)

    return shared_pvs


def main():
    # query API to get list of sections
    lattice = get_lattice()
    pvs = construct_pvs_from_lattice(lattice)
    conf = get_server_conf()
    with Server(providers=[pvs], conf=conf) as server:
        while True:
            try:
                time.sleep(1)  # Keep the server running
            except KeyboardInterrupt:
                print("Server stopped by user.")
                server.stop()
                break


if __name__ == "__main__":
    main()
