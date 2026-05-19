import time
from datetime import datetime
from janus_common.schemas.elements import Lattice
from typing import Tuple
from janus_common.utils.comms_handler import (
    get_lattice,
    patch_lattice,
    send_prior_settings,
)
from janus_common.utils.kafka_restframe import API
from janus_common.utils.comms_handler import lattice_exists
from set_lattice_from_epics import EPICSToLattice
from set_epics_from_lattice import LatticeToEPICS


class Sender(API):
    def __init__(self):
        super().__init__(group_id="epics-to-lattice")
        self.lattice_sent = False
        self.facility = "CLARA"
        self.e2l = EPICSToLattice()
        self.l2e = LatticeToEPICS()

    def get_current_lattice(self) -> Lattice:
        return get_lattice()

    def get_lattice(self, uuid: str = None) -> Lattice:
        return get_lattice(uuid=uuid)

    def lattice_exists(self, lattice: Lattice) -> Tuple[bool, str | None]:
        """
        Check if the current lattice settings match any lattices in the database
        using the find_lattices GraphQL resolver.

        Returns:
            True if a matching lattice is found, False otherwise
        """
        try:
            # Prepare magnet and cavity filters from current lattice

            # Build filters from EPICS values
            magnet_filters = self.e2l.build_magnet_filters(lattice)
            cavity_filters = self.e2l.build_cavity_filters(lattice)
            section_filters = self.e2l.build_section_filters(lattice)
            initial_condition_sections = (
                lattice.set_initial_conditions if lattice.set_initial_conditions else ""
            )
            generator_filter = self.e2l.build_generator_filters(lattice)
            exists, uuid = lattice_exists(
                facility=self.facility,
                set_initial_conditions=initial_condition_sections,
                magnet_filter=magnet_filters,
                cavity_filter=cavity_filters,
                section_filter=section_filters,
                generator_filter=generator_filter,
            )
            return exists, uuid
        except Exception as e:
            print(f"Error checking lattice: {e}")
            return False, None

    def on_msg(self, uuid, message):
        handlers = {
            "lattice_added": self._handle_lattice_added,
            "lattice_ready": self._handle_lattice_sent,
        }
        handler = handlers.get(message.topic)
        if handler:
            handler(uuid, message)
        else:
            print(f"Unknown topic: {message.topic}")

    def _handle_lattice_added(self, uuid, message):
        self.lattice_sent = False

    def _handle_lattice_sent(self, uuid, message):
        self.lattice_sent = True

    def initialise(self, lattice: Lattice) -> None:
        self.l2e.initialise_all_magnets(lattice=lattice)
        print("initialised magnets")
        self.l2e.initialise_all_cavities(lattice=lattice)
        print("initialised phase for all cavities")
        self.l2e.initialise_all_sim_codes(lattice=lattice)
        print("initialised simulation codes for all sections")
        self.l2e.initialise_generator(lattice=lattice)
        print("initialised generator")

    def trigger_lattice_update(self) -> None:
        if self.e2l.is_tracking:
            print("Simulation is currently tracking, skipping lattice update.")
            return
        if self.lattice_sent:
            return
        current_lattice = self.get_current_lattice()
        changed_lattice = self.e2l.set_lattice_from_epics(current_lattice)
        lattice_exists, uuid = self.lattice_exists(changed_lattice)
        if not lattice_exists:
            print("Lattice has changed, updating comms with new lattice.")
            current_lattice.success = None
            patch_lattice(
                lattice=changed_lattice,
            )
        else:
            existing_lattice = self.get_lattice(uuid)
            if current_lattice.uuid != existing_lattice.uuid:
                print(f"Found previous run: {existing_lattice.uuid}")
                send_prior_settings(existing_lattice)

    def loop(self) -> None:
        if not self.e2l.is_tracking:
            if self.e2l.is_tracking_triggered:
                if not self.e2l.is_tracking_started:
                    return
                else:
                    self.trigger_lattice_update()
                    self.e2l.tracking_start_state = "BYPASS"
                    return
            if self.e2l.is_tracking_auto:
                self.trigger_lattice_update()


if __name__ == "__main__":
    sender = Sender()
    interval_s = 1.0
    print("initialised sender (magnets connected.)")
    while sender.get_current_lattice() is None:
        time.sleep(interval_s)
    latest_uuid = sender.get_latest_run_uuid()
    current_lattice = sender.get_lattice(uuid=latest_uuid)
    sender.initialise(lattice=current_lattice)
    sender.subscribe(["lattice_ready", "lattice_added"])
    last_update = datetime.now()
    while True:
        if (datetime.now() - last_update).total_seconds() < interval_s:
            time.sleep(0.1 * interval_s)
        else:
            sender.loop()
            last_update = datetime.now()
