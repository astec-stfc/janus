import os
import sys
import time
from datetime import datetime
from janus_common.schemas.elements import Lattice, SimulationTrigger
from typing import Tuple
from janus_common.utils.comms_handler import (
    get_lattice,
    patch_lattice,
    send_prior_settings,
)
from janus_common.utils.flow_log import flow_log
from janus_common.utils.kafka_restframe import API
from janus_common.utils.comms_handler import lattice_exists
from set_lattice_from_epics import EPICSToLattice
from set_epics_from_lattice import LatticeToEPICS

CLIENT_ID = os.getenv("CLIENT_ID")
if not CLIENT_ID:
    print("ERROR: CLIENT_ID is not set. Set a unique name: export CLIENT_ID=yourname")
    sys.exit(1)


class Sender(API):
    def __init__(self):
        super().__init__(group_id="epics-to-lattice")
        self.facility = "JFEL"
        self.e2l = EPICSToLattice()
        self.l2e = LatticeToEPICS()
        self._local_lattice: Lattice | None = None
        self._trigger_subscription = None

    def get_current_lattice(self) -> Lattice:
        if self._local_lattice is not None:
            return self._local_lattice
        return get_lattice()

    def get_lattice(self, uuid: str = None) -> Lattice:
        return get_lattice(uuid=uuid)

    def current_epics_settings_exist_in_db(
        self, lattice: Lattice
    ) -> Tuple[bool, str | None]:
        """
        Check if the current lattice settings from epics match any lattices in the database
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

    def lattice_settings(self, lattice: Lattice) -> dict:
        return {
            "set_initial_conditions": lattice.set_initial_conditions or "",
            "magnets": self.e2l.build_magnet_filters(lattice),
            "cavities": self.e2l.build_cavity_filters(lattice),
            "sections": self.e2l.build_section_filters(lattice),
            "generator": self.e2l.build_generator_filters(lattice),
        }

    def copy_lattice_for_epics_update(self, lattice: Lattice) -> Lattice:
        return Lattice.model_validate(lattice.model_dump())

    def initialise_pvs_from_lattice(self, lattice: Lattice) -> None:
        self.l2e.initialise_all_magnets(lattice=lattice)
        print("initialised magnets")
        self.l2e.initialise_all_cavities(lattice=lattice)
        print("initialised phase for all cavities")
        self.l2e.initialise_all_photon_monitors(lattice=lattice)
        print("initialised all photon monitors")
        self.l2e.initialise_all_sim_codes(lattice=lattice)
        print("initialised simulation codes for all sections")
        self.l2e.initialise_generator(lattice=lattice)
        print("initialised generator")
        self._local_lattice = lattice

    def initialise_pvs_from_latest_run(self) -> None:
        latest_uuid = self.get_latest_run_uuid()
        initial_lattice = self.get_lattice(uuid=latest_uuid)
        if initial_lattice is None:
            raise RuntimeError(f"No lattice found for latest uuid: {latest_uuid}")
        self.initialise_pvs_from_lattice(initial_lattice)

    def trigger_lattice_update(self) -> None:
        if self.e2l.is_tracking:
            # If there's a 2nd PV change while 1st PV change is tracking,
            # it will be caught after 1st PV change finishes tracking
            print("Simulation is currently tracking, skipping lattice update.")
            return

        baseline_lattice = self.get_current_lattice()
        if baseline_lattice is None:
            return

        baseline_settings = self.lattice_settings(baseline_lattice)
        epics_lattice = self.e2l.set_lattice_from_epics(
            self.copy_lattice_for_epics_update(baseline_lattice)
        )
        if self.lattice_settings(epics_lattice) == baseline_settings:
            return
        stored_run_exists, existing_uuid = self.current_epics_settings_exist_in_db(
            epics_lattice
        )
        if not stored_run_exists:
            print("Lattice has changed, updating comms with new lattice.")
            epics_lattice.success = None  # new untracked lattice so reset success flag
            epics_lattice.client_id = CLIENT_ID
            flow_log(
                "G01 epics.change",
                "C1/3",
                client_id=CLIENT_ID,
                current="EPICS magnet change detected, PATCHing updated lattice to the lattice API",
                next_step="lattice API to publish a message to topic 'lattice_ready'",
            )
            patch_lattice(
                lattice=epics_lattice,
            )
            self._local_lattice = epics_lattice
        else:
            stored_run = self.get_lattice(existing_uuid)
            if stored_run is None:
                return
            stored_run.client_id = CLIENT_ID
            # EPICS already matches a completed database run. Apply those stored
            # results once, then remember that run as this client's new baseline.
            if baseline_lattice.uuid != stored_run.uuid:
                print(f"Current EPICS settings match stored run: {stored_run.uuid}")
                send_prior_settings(stored_run)
            # baseline lattice will point to _local_lattice on next poll
            self._local_lattice = stored_run

    def on_simulation_start_changed(self, value) -> None:
        if isinstance(value, Exception):
            print(f"{self.e2l.simulation_translator.start_pv.name} monitor error: {value}")
            return
        if not self.e2l.is_tracking_triggered:
            return
        value = self.e2l.epics_helper.epics_scalar(value)
        if value != SimulationTrigger.ACTIVATE.value:
            return

        try:
            self.trigger_lattice_update()
        finally:
            self.e2l.tracking_start_state = SimulationTrigger.BYPASS.value

    def start_trigger_monitor(self) -> None:
        if self._trigger_subscription is not None:
            return
        self._trigger_subscription = self.e2l._ctx.monitor(
            self.e2l.simulation_translator.start_pv.name,
            self.on_simulation_start_changed,
        )

    def close_trigger_monitor(self) -> None:
        if self._trigger_subscription is None:
            return
        self._trigger_subscription.close()
        self._trigger_subscription = None

    def loop(self) -> None:
        if self.e2l.is_tracking_auto:
            self.trigger_lattice_update()


if __name__ == "__main__":
    sender = Sender()
    interval_s = 1.0
    print("initialised sender (magnets connected.)")
    while sender.get_current_lattice() is None:
        time.sleep(interval_s)
    while not sender.e2l.epics_helper.is_epics_alive:
        time.sleep(interval_s)
    print("Simulation PVs Available")
    sender.initialise_pvs_from_latest_run()
    sender.start_trigger_monitor()
    last_update = datetime.now()
    try:
        while True:
            if (datetime.now() - last_update).total_seconds() < interval_s:
                time.sleep(0.1 * interval_s)
            else:
                sender.loop()
                last_update = datetime.now()
    finally:
        sender.close_trigger_monitor()
