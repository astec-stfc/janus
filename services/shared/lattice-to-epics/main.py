import time
from typing import List
from janus_common.utils.helpers import EPICSHelper
from janus_common.pv.translate import (
    ElementToPV,
    GeneratorToPV,
    SectionToPV,
    SimulationToPV,
    LatticeToPV,
)
from p4p.client.thread import Context
from janus_common.schemas import elements
import requests
from janus_common.utils.kafka_restframe import API
from janus_common.utils.comms_handler import get_lattice


class Sender(API):

    def __init__(self):
        super().__init__(group_id="lattice-to-epics")
        self._ctx = Context("pva")
        self.epics_helper = EPICSHelper(self._ctx)
        self._current_uuid = None
        self.simulation_translator = SimulationToPV()
        self.lattice_translator = LatticeToPV()
        self.generator_translator = GeneratorToPV()

    def set_results(self, uuid: str) -> None:
        """
        Initialise the results by getting the latest lattice
        and setting all sections
        """
        if uuid == self._current_uuid:
            # No new results to set, return early
            return
        else:
            self._current_uuid = uuid
            try:
                lattice = get_lattice(uuid=uuid)
                updates = []
                if lattice is not None:
                    self.set_tracking_success(lattice=lattice)
                    [
                        updates.extend(self.get_section_results(section))
                        for section in lattice.sections.values()
                    ]
                    updates.extend(self.get_lattice_beam_summary(lattice=lattice))
                    updates.extend(self.get_lattice_generator(lattice=lattice))
                    updates.extend(self.get_lattice_uuid(lattice=lattice))
                    self.epics_helper.set_pv_updates(updates)
            except requests.exceptions.JSONDecodeError as e:
                print("Could not decode lattice from restframe")
                print(e)

    def get_section_results(self, section: elements.Section):
        """Get the results for a section and prepare PV updates"""
        pv_updates = []
        for element in section.get_elements():
            translator = ElementToPV(element)
            pv_metadata = translator.element_pv_metadata
            pv_updates += [
                (
                    (m.name, m.get_schema_value(element))
                    if m.get_schema_value(element) is not None
                    else (m.name, m.value_as_type(-999))
                )
                for m in pv_metadata
            ]
        translator = SectionToPV(section)
        pv_metadata = translator.section_pv_metadata
        pv_updates += [
            (
                (m.name, m.get_schema_value(section))
                if m.get_schema_value(section) is not None
                else (m.name, m.value_as_type(-999))
            )
            for m in pv_metadata
        ]
        return pv_updates

    def get_lattice_uuid(self, lattice: elements.Lattice) -> List:
        """Get the simulation code PV for a given section"""
        updates = []
        updates.append((self.simulation_translator.uuid_pv.name, lattice.uuid))
        return updates

    def set_tracking_success(self, lattice: elements.Lattice) -> None:
        """Get the tracking success PV for a given lattice"""
        success = lattice.success if lattice.success is not None else False
        if success:
            # Tracking completed successfully
            self.epics_helper.put_pv(
                pvname=self.simulation_translator.status_pv.name,
                value=0,
            )
        else:
            # Error state being set for unsuccessful tracking
            self.epics_helper.put_pv(
                pvname=self.simulation_translator.status_pv.name,
                value=2,
            )

    def get_lattice_generator(self, lattice: elements.Lattice) -> List:
        if lattice.generator is None:
            return []
        if isinstance(lattice.generator, elements.Generator):
            pv_metadata = self.generator_translator.generator_pv_metadata
            return [
                (
                    (m.name, m.get_schema_value(lattice.generator))
                    if m.get_schema_value(lattice.generator) is not None
                    else (m.name, m.value_as_type(-999))
                )
                for m in pv_metadata
            ]

    def get_lattice_beam_summary(self, lattice: elements.Lattice) -> List:
        """Get the beam summary PVs for a given section"""
        if lattice.beam_summary is not None:
            beam_summary_metadata = self.lattice_translator.beam_summary_pv_metadata
            return [
                (
                    m.name,
                    m.get_schema_value(lattice)
                    if m.get_schema_value(lattice) is not None
                    else m.value_as_type(-999),
                )
                for m in beam_summary_metadata
            ]

    def on_msg(self, uuid, message):
        """Route messages based on topic"""
        handlers = {
            "tracking_started": self._handle_tracking_started,
            "lattice_added": self._handle_lattice_added,
            "lattice_updated": self._handle_lattice_updated,
        }

        handler = handlers.get(message.topic)
        if handler:
            handler(uuid, message)
        else:
            print(f"Unknown topic: {message.topic}")

    def _handle_tracking_started(self, uuid, message):
        """Handle the tracking started message by setting the simulation status to running"""
        self.epics_helper.put_pv(
            pvname=self.simulation_translator.status_pv.name,
            value=1,
        )

    def _handle_lattice_added(self, uuid, message):
        """Handle the lattice added message by setting the results for the new lattice"""
        uuid = uuid["uuid"]
        self.set_results(uuid=uuid)

    def _handle_lattice_updated(self, uuid, message):
        """Handle the lattice updated message by setting the results for the lattice"""
        print("Lattice updated message received, updating results")
        print("Message UUID: ", uuid)
        uuid = uuid["uuid"]
        self.set_results(uuid=uuid)

    def initialise(self):
        while not self.epics_helper.is_epics_alive:
            time.sleep(0.5)
        print("Simulation PVs are available.")


if __name__ == "__main__":
    sender = Sender()
    sender.initialise()
    sender.subscribe(["lattice_added", "tracking_started", "lattice_updated"])
    sender.forever_loop()
