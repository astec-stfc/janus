import os
import sys
import logging
import time
from typing import List
from concurrent.futures import ThreadPoolExecutor
from janus_common.utils.helpers import EPICSHelper, EPICSStreamer
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
from janus_common.utils.flow_log import flow_log


CLIENT_ID = os.getenv("CLIENT_ID")
if not CLIENT_ID:
    print("ERROR: CLIENT_ID is not set. Set a unique name: export CLIENT_ID=yourname")
    sys.exit(1)


class Sender(API):

    def __init__(self):
        # Group ID must be unique per client so that every lattice-to-epics
        # instance sees every Kafka message and can filter by client_id locally.
        super().__init__(group_id=f"lattice-to-epics-{CLIENT_ID}")
        self._ctx = Context("pva")
        self.epics_helper = EPICSHelper(self._ctx)
        self.epics_streamer = EPICSStreamer(self.epics_helper)
        self._current_uuid = None
        self._last_result_timestamp = None
        self._completed_request_ids = set()
        self.simulation_translator = SimulationToPV()
        self.lattice_translator = LatticeToPV()
        self.generator_translator = GeneratorToPV()
        self._element_translators = {}
        self._section_translators = {}
        self._section_executor = ThreadPoolExecutor(max_workers=8)

    def set_results(self, uuid: str = None) -> bool:
        """
        Fetch the lattice for uuid, write all section PVs in parallel via
        the streamer, then write beam-summary / generator / uuid PVs.
        """
        try:
            t0 = time.time()
            lattice = get_lattice(uuid=uuid, arrays_as_lists=False)
            if lattice is None:
                return False
            t_fetch = time.time()

            stream = self.epics_streamer
            stream.flush()  # clear any leftover state from a previous failed call
            list(self._section_executor.map(
                lambda s: self.get_section_results_fast(s, stream),
                lattice.sections.values(),
            ))
            stream.flush()
            t_sections = time.time()

            updates = []
            updates.extend(self.get_lattice_beam_summary(lattice=lattice))
            updates.extend(self.get_lattice_generator(lattice=lattice))
            updates.extend(self.get_lattice_uuid(lattice=lattice))
            self.epics_helper.set_pv_updates(updates)
            t_updates = time.time()

            self.set_tracking_success(lattice=lattice)
            self._current_uuid = uuid
            t_done = time.time()
            print(
                "lattice-to-epics set_results timings "
                f"client={CLIENT_ID} "
                f"uuid={uuid} "
                f"fetch_decode={t_fetch - t0:.3f}s "
                f"sections_write={t_sections - t_fetch:.3f}s "
                f"summary_write={t_updates - t_sections:.3f}s "
                f"status_write={t_done - t_updates:.3f}s "
                f"total={t_done - t0:.3f}s"
            )
            return True
        except requests.exceptions.JSONDecodeError as e:
            print("Could not decode lattice from restframe")
            print(e)
            return False

    def get_section_results_fast(self, section: elements.Section, stream: EPICSStreamer) -> None:
        """Push all PV updates for a section directly into the streamer."""
        for element in section.get_elements():
            translator = self._element_translators.get(element.name)
            if translator is None:
                translator = ElementToPV(element)
                self._element_translators[element.name] = translator
            for m in translator.element_pv_metadata:
                v = m.get_schema_value(element)
                stream.push(m.name, v if v is not None else m.value_as_type(-999))
        translator = self._section_translators.get(section.name)
        if translator is None:
            translator = SectionToPV(section)
            self._section_translators[section.name] = translator
        for m in translator.section_pv_metadata:
            v = m.get_schema_value(section)
            stream.push(m.name, v if v is not None else m.value_as_type(-999))

    def get_lattice_uuid(self, lattice: elements.Lattice) -> List:
        """Get the simulation code PV for a given section"""
        updates = []
        updates.append((self.simulation_translator.uuid_pv.name, lattice.uuid))
        return updates

    def set_tracking_success(self, lattice: elements.Lattice) -> None:
        """Get the tracking success PV for a given lattice"""
        success = lattice.success if lattice.success is not None else False
        status_value = 0 if success else 2

        # Keep the completion signal synchronous and reliable.
        self.epics_helper.put_pv(
            pvname=self.simulation_translator.status_pv.name,
            value=status_value,
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
        return []

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
        return []

    def on_msg(self, event, message):
        """Route messages based on topic"""
        msg_client_id = event.get("client_id")
        if msg_client_id != CLIENT_ID:
            print(
                f"[--] client: {CLIENT_ID} | message on topic '{message.topic}' was published for client '{msg_client_id}' -- ignoring"
            )
            return
        handlers = {
            "tracking_started": self._handle_tracking_started,
            "lattice_added": self._handle_lattice_added,
            "lattice_updated": self._handle_lattice_updated,
            "new_results": self._handle_new_results,
        }

        handler = handlers.get(message.topic)
        if handler:
            handler(event, message)
        else:
            print(f"Unknown topic: {message.topic}")

    def _handle_tracking_started(self, event, message):
        """Handle the tracking started message by setting the simulation status to running"""
        request_id = event.get("request_id")
        # for new sim:
        # - lattice_api publishes to `lattice_added` with request_id
        # - l2r publishes to `new_results` after writing to db
        # so both carry same request, but we don't want both setting SIM_STATUS -> 1
        if request_id and request_id in self._completed_request_ids:
            print(
                f"[--] client: {CLIENT_ID} | stale tracking_started ignored for completed request_id '{request_id}'"
            )
            return
        if (
            self._last_result_timestamp is not None
            and message.timestamp <= self._last_result_timestamp
        ):
            print(
                f"[--] client: {CLIENT_ID} | stale tracking_started ignored because a later result was already applied"
            )
            return
        flow_log(
            "G05 tracking.observe",
            "C2/3",
            client_id=CLIENT_ID,
            request_id=request_id,
            current="consumed message from topic 'tracking_started', setting SIMULATION:STATUS to TRACKING in EPICS",
            next_step="restframe to complete simulation and publish to topic 'tracking_finished'",
        )
        self.epics_helper.put_pv(
            pvname=self.simulation_translator.status_pv.name,
            value=1,
        )

    def _handle_lattice_added(self, event, message):
        """Handle lattice-api confirming that tracked results were stored."""
        lattice_uuid = event["uuid"]
        self._handle_results(
            lattice_uuid,
            event.get("request_id"),
            message.topic,
            message.timestamp,
        )

    def _handle_lattice_updated(self, event, message):
        """Handle stored-run reuse by setting the results for the lattice."""
        lattice_uuid = event["uuid"]
        self._handle_results(
            lattice_uuid,
            event.get("request_id"),
            message.topic,
            message.timestamp,
        )

    def _handle_new_results(self, event, message):
        """Handle post-write completion signal using the same result path."""
        lattice_uuid = event["uuid"]
        self._handle_results(
            lattice_uuid,
            event.get("request_id"),
            message.topic,
            message.timestamp,
        )

    def _handle_results(
        self, lattice_uuid: str, request_id: str, topic: str, timestamp: int
    ):
        """Apply completed results once, even though two completion topics may arrive."""
        # New simulations send both lattice_added and new_results for the same request.
        # If one has already applied the results, ignore the other.
        if request_id and request_id in self._completed_request_ids:
            return
        # If this exact lattice UUID is already applied on this client, there
        # is no need to write all result PVs again.
        if lattice_uuid == self._current_uuid:
            return
        if self.set_results(lattice_uuid):
            if request_id:
                self._completed_request_ids.add(request_id)
            self._last_result_timestamp = timestamp
            flow_log(
                "G09 results.apply",
                "C3/3",
                client_id=CLIENT_ID,
                request_id=request_id,
                current=f"consumed message from topic '{topic}', writing simulation results to EPICS PVs and setting SIMULATION:STATUS back to 0",
                next_step="round trip complete",
            )

    def initialise(self):
        while not self.epics_helper.is_epics_alive:
            time.sleep(0.5)
        print("Simulation PVs are available.")
        # initialise SIM PVs with most recent lattice
        self.set_results()


if __name__ == "__main__":
    sender = Sender()
    sender.initialise()
    sender.subscribe(
        ["lattice_added", "tracking_started", "lattice_updated", "new_results"]
    )
    sender.forever_loop()
