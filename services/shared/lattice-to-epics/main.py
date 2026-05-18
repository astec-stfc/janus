import logging
import time
from typing import Any, List, Tuple
from common.helpers import EPICSHelper
from p4p.client.thread import Context
from schemas import elements
import requests
from common.kafka_restframe import API
from common.comms_handler import get_lattice


class Sender(API):

    def __init__(self):
        super().__init__(group_id="lattice-to-epics")
        self._ctx = Context("pva")
        self.epics_helper = EPICSHelper(self._ctx)
        self._current_uuid = None

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
                    [
                        updates.extend(
                            self.get_section_simulation_codes(section=section)
                        )
                        for section in lattice.sections.values()
                    ]
                    for section in lattice.sections.values():
                        if section.name in lattice.set_initial_conditions:
                            updates.extend(
                                self.get_section_initial_conditions(section=section)
                            )
                    updates.extend(self.get_lattice_beam_summary(lattice=lattice))
                    # updates.extend(self.get_lattice_set_initial_conditions(lattice=lattice))
                    updates.extend(self.get_lattice_generator(lattice=lattice))
                    updates.extend(self.get_lattice_uuid(lattice=lattice))
                    self.epics_helper.set_pv_updates(updates)
            except requests.exceptions.JSONDecodeError as e:
                print("Could not decode lattice from restframe")
                print(e)

    def get_non_native_type_pv_name_and_value(
        self,
        element_name: str,
        field_type: elements.Twiss | elements.Sigma | elements.Centroid | elements.Beam,
        field_instance=None,
    ) -> List[Tuple[str, Any]]:
        """Get the PV name and value for a non-native type field"""
        if (
            field_type is not elements.Twiss
            and field_type is not elements.Sigma
            and field_type is not elements.Centroid
            and field_type is not elements.Beam
        ) or not field_instance:
            return [(None, None)]
        updates = []
        for field_name, _ in field_type.__pydantic_fields__.items():
            # Construct a PV name from the field
            pv_name = f"SIM-{element_name}:{field_type.__name__.upper()}:{field_name.capitalize()}"
            field_value = getattr(field_instance, field_name)
            if field_value:
                updates.append((pv_name, field_value))
            else:
                # If the field value is None, we can choose to set a default value or skip the update
                updates.append((pv_name, -999))
        return updates

    def get_section_results(self, section: elements.Section):
        """Get the results for a section and prepare PV updates"""
        pv_updates = []
        for element in section.get_elements():
            fields = {
                field_name: field
                for field_name, field in element.__class__.model_fields.items()
                if field_name in element.model_fields_set
            }
            for field_name, _ in fields.items():
                update = [(None, None)]
                match field_name:
                    case "twiss":
                        twiss = element.twiss
                        update = self.get_non_native_type_pv_name_and_value(
                            element_name=element.name,
                            field_type=elements.Twiss,
                            field_instance=twiss,
                        )
                    case "sigma":
                        sigma = element.sigma
                        update = self.get_non_native_type_pv_name_and_value(
                            element_name=element.name,
                            field_type=elements.Sigma,
                            field_instance=sigma,
                        )
                    case "centroid":
                        centroid = element.centroid
                        update = self.get_non_native_type_pv_name_and_value(
                            element_name=element.name,
                            field_type=elements.Centroid,
                            field_instance=centroid,
                        )
                    case "beam":
                        beam = element.beam
                        update = self.get_non_native_type_pv_name_and_value(
                            element_name=element.name,
                            field_type=elements.Beam,
                            field_instance=beam,
                        )
                    case "camera":
                        pass
                    case _:
                        pv_name = f"SIM-{element.name}:{field_name.capitalize()}"
                        result = getattr(element, field_name)
                        if result:
                            update = [(pv_name, result)]
                for i in update:
                    if i != (None, None):
                        pv_updates.append(i)
        return pv_updates

    def get_lattice_uuid(self, lattice: elements.Lattice) -> List:
        """Get the simulation code PV for a given section"""
        self.epics_helper.put_pv(
            pvname=f"SIM-{lattice.facility}:UUID",
            value=lattice.uuid,
        )
        updates = []
        updates.append((f"SIM-{lattice.facility}:UUID", lattice.uuid))
        return updates

    def get_section_simulation_codes(self, section: elements.Section) -> List:
        """Get the simulation code PV for a given section"""
        self.epics_helper.put_pv(
            pvname=f"VM-{section.name}-SIMULATION:CODE",
            value=section.model,
        )
        updates = []
        updates.append((f"VM-{section.name}-SIMULATION:CODE", section.model))
        return updates

    def set_tracking_success(self, lattice: elements.Lattice) -> None:
        """Get the tracking success PV for a given lattice"""
        success = lattice.success if lattice.success is not None else False
        if success:
            # Tracking completed successfully
            self.epics_helper.put_pv(
                pvname="SIMULATION:STATUS",
                value=0,
            )
        else:
            # Error state being set for unsuccessful tracking
            self.epics_helper.put_pv(
                pvname="SIMULATION:STATUS",
                value=2,
            )

    def get_section_initial_conditions(self, section: elements.Section) -> List:
        """Get the initial twiss settings PVs for a given section"""
        updates = []
        twiss_to_set = []
        for tw in ["beta", "alpha", "nemit"]:
            for plane in ["x", "y"]:
                suffix = f"{tw.upper()}_{plane.upper()}"
                name = f"SIM-{section.name}-INITIAL-CONDITIONS:{suffix}"
                self.epics_helper.put_pv(
                    pvname=name,
                    value=getattr(section.initial_conditions, f"{tw}_{plane}"),
                )
                twiss_to_set.append(
                    (name, getattr(section.initial_conditions, f"{tw}_{plane}"))
                )
        if len(twiss_to_set) == 6:
            return twiss_to_set
        return updates

    def get_lattice_generator(self, lattice: elements.Lattice) -> List:
        updates = []
        if isinstance(lattice.generator, elements.Generator):
            for k, v in lattice.generator.model_dump().items():
                if k not in ["uuid", "enable"]:
                    pvname = f"SIM-GENERATOR:{k.upper().replace('_', '-')}"
                    self.epics_helper.put_pv(
                        pvname=pvname,
                        value=v,
                    )
                    updates.append((pvname, getattr(lattice.generator, k)))
        return updates

    # def get_lattice_set_initial_conditions(self, lattice: elements.Lattice) -> List:
    #     self.epics_helper.put_pv(
    #         pvname=f"SIM-{lattice.facility}-INITIAL-CONDITIONS:ENABLE",
    #         value=lattice.set_initial_conditions,
    #     )
    #     updates = [
    #         (
    #             f"SIM-{lattice.facility}-INITIAL-CONDITIONS:ENABLE",
    #             lattice.set_initial_conditions,
    #         )
    #     ]
    #     return updates

    def get_lattice_beam_summary(self, lattice: elements.Lattice) -> List:
        """Get the beam summary PVs for a given section"""
        updates = []
        if lattice.beam_summary is not None:
            for beam_stat, value in dict(lattice.beam_summary).items():
                if value is not None:
                    suffix = self.epics_helper.abbreviations.get(
                        beam_stat, beam_stat.upper()
                    )
                    pv_name = f"VM-{lattice.facility}-{suffix}"
                    logging.info(beam_stat)
                    updates.append((pv_name, value))
                else:
                    logging.info(
                        "Value for %s was None, not updating PV",
                        beam_stat,
                    )
        return updates

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
        self.epics_helper.set_simulation_status(1)

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
