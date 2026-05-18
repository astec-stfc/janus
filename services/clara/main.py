import time
from datetime import datetime
from schemas.elements import Lattice
from typing import Tuple
import requests
from common.comms_handler import (
    get_lattice,
    patch_lattice,
    send_prior_settings,
)
from common.kafka_restframe import API
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

    def lattice_exists(self) -> Tuple[bool, str | None]:
        """
        Check if the current lattice settings match any lattices in the database
        using the find_lattices GraphQL resolver.

        Returns:
            True if a matching lattice is found, False otherwise
        """
        try:
            # Prepare magnet and cavity filters from current lattice

            # Build filters from EPICS values
            magnet_filters = self.e2l.build_magnet_filters()
            cavity_filters = self.e2l.build_cavity_filters()
            section_filters = self.e2l.build_section_filters()
            initial_condition_sections = self.e2l.initial_condition_sections
            generator_filter = self.e2l.build_generator_filters()

            # Make GraphQL query to find_lattices
            query = """
            query FindLattices($facility: String!, $setInitialConditions: String!,  $magnetFilter: [MagnetInput!]!, $cavityFilter: [CavityInput!]!, $sectionFilter: [SectionInput!]!, $generatorFilter: GeneratorInput!) {
                findLattices(facility: $facility, setInitialConditions: $setInitialConditions, magnetFilter: $magnetFilter, cavityFilter: $cavityFilter, sectionFilter: $sectionFilter, generatorFilter: $generatorFilter) {
                    uuid
                    facility
                    sectionCount
                }
            }
            """
            variables = {
                "facility": self.facility,
                "setInitialConditions": initial_condition_sections,
                "magnetFilter": magnet_filters,
                "cavityFilter": cavity_filters,
                "sectionFilter": section_filters,
                "generatorFilter": generator_filter,
            }

            # Send GraphQL request
            lattice_api_url = "http://lattice_api:5000/graphql"
            response = requests.post(
                lattice_api_url,
                json={"query": query, "variables": variables},
                timeout=10,
            )

            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                print(f"GraphQL error: {data['errors']}")
                return False, None

            # Check if any matching lattices found
            matching_lattices = data.get("data", {}).get("findLattices", [])
            if matching_lattices:
                # return first found lattice uuid
                return True, matching_lattices[0]["uuid"]
            else:
                print("No matching lattices found in database")
                return False, None

        except requests.exceptions.RequestException as e:
            print(f"Error connecting to lattice API: {e}")
            return False, None
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
        self.l2e.initialise_all_magnets(lattice=current_lattice)
        print("initialised magnets")
        self.l2e.initialise_all_cavities(lattice=current_lattice)
        print("initialised phase for all cavities")
        self.l2e.initialise_all_sim_codes(lattice=current_lattice)
        print("initialised simulation codes for all sections")
        self.l2e.initialise_generator(lattice=current_lattice)
        print("initialised generator")

    def trigger_lattice_update(self) -> None:
        if self.e2l.is_tracking:
            print("Simulation is currently tracking, skipping lattice update.")
            return
        if self.lattice_sent:
            return
        current_lattice = self.get_current_lattice()
        lattice_exists, uuid = self.lattice_exists()
        if not lattice_exists:
            changed_lattice = self.e2l.set_lattice_from_epics(current_lattice)
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
