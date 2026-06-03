import asyncio
import os
import sys
from janus_common.schemas import elements
from janus_common.schemas.elements import Lattice, Magnet, MagnetEnum, Cavity
from janus_common.pv.translate import SectionToPV
from random import random
from p4p.client.asyncio import Context
from janus_common.utils.kafka_restframe import API
from janus_common.utils.comms_handler import patch_lattice, get_lattice
from janus_common.utils.flow_log import flow_log

CLIENT_ID = os.getenv("CLIENT_ID")
if not CLIENT_ID:
    print("ERROR: CLIENT_ID is not set. Set a unique name: export CLIENT_ID=yourname")
    sys.exit(1)


class Sender(API):
    def __init__(self):
        super().__init__(group_id="isis_to_comm")
        self._pv_to_check = (
            "ISIS:SIM:SEED"  # TODO This is where we will add all the IOCs
        )
        self._ctx = Context("pva")
        self._current_value = None  # self._ctx.get(self._pv_to_check)
        self.sub = None
        self.counter = True

    def _randomise_lattice(self, lattice: Lattice) -> None:
        from random import randint

        for magnet in lattice.get_elements_dict(Magnet).values():
            if magnet.subtype == MagnetEnum.quadrupole:
                magnet.KnL[1] = random()
                magnet.momentum = random()

        for cavity in lattice.get_elements_dict(Cavity).values():
            cavity.phase = randint(-90, 90)

    async def has_sim_seed_updated(self) -> bool:
        """This is where you would compare the current lattice with the epics settings"""
        try:
            _value = await asyncio.wait_for(
                self._ctx.get(self._pv_to_check), timeout=10
            )
        except TimeoutError as e:
            print(f"Timeout while getting value for {self._pv_to_check}: {str(e)}")
            return False
        else:
            _changed = _value != self._current_value
            if _changed:
                self._current_value = _value
            return _changed

    async def initialise_all_sim_codes(self, lattice: Lattice) -> None:
        for section in lattice.sections.values():
            translator = SectionToPV(section)
            for m in translator.section_pv_metadata:
                value = m.get_schema_value(section)
                if value is not None:
                    try:
                        await asyncio.wait_for(self._ctx.put(m.name, value), timeout=10)
                    except TimeoutError as e:
                        print(
                            f"Timeout while setting SIMULATION:CODE for {section.name}: {str(e)}"
                        )
                        continue

    async def set_section_from_epics(self, lattice: Lattice) -> None:
        for section in lattice.sections.values():
            translator = SectionToPV(section)
            pv_metadata = translator.section_pv_metadata
            for m in pv_metadata:
                try:
                    epics_result = await asyncio.wait_for(
                        self._ctx.get(m.name), timeout=10
                    )
                except TimeoutError as e:
                    print(
                        f"Timeout while getting {m.name} for {section.name}: {str(e)}"
                    )
                    continue
                if (
                    not isinstance(epics_result, TimeoutError)
                    and epics_result != "undefined"
                    and epics_result != ""
                ):
                    current_value = m.get_schema_value(section)
                    if current_value != epics_result:
                        m.set_schema_value(section, epics_result)
        return lattice

    async def has_lattice_changed(self, lattice: elements.Lattice) -> bool:
        lattice_with_changes_from_epics = await self.set_section_from_epics(lattice)
        return get_lattice() != lattice_with_changes_from_epics

    async def start(self):
        initial_lattice = get_lattice()
        if initial_lattice is None:
            raise RuntimeError("Could not fetch initial lattice to initialise ISIS PVs")
        await self.initialise_all_sim_codes(initial_lattice)
        self.sub = self._ctx.monitor(self._pv_to_check, self.on_epics_update)
        while True:
            await asyncio.sleep(3600)

    async def on_epics_update(self, value):
        print(f"Received update for {self._pv_to_check}: {value}")
        current_lattice = (
            get_lattice()
        )  # This gets you the latest lattice available, I think dunno, if you use self.get_lattice it uses the restframe API and you get screwed, that is on me, I could change it but I am a simple man
        if self.counter:
            print(
                "FIRST RUN, JUST SENDING LATTICE TO COMMS WITHOUT CHECKING FOR CHANGES"
            )
            self.counter = False
            return
        if await self.has_sim_seed_updated():
            print("SIM SEED UPDATED, RANDOMISING LATTICE")
            self._randomise_lattice(lattice=current_lattice)

        if await self.has_lattice_changed(current_lattice):
            current_lattice.client_id = CLIENT_ID
            flow_log(
                "G01 epics.change",
                "C1/3",
                client_id=CLIENT_ID,
                current="EPICS setting change detected, PATCHing updated lattice to the lattice API",
                next_step="lattice API to publish a message to topic 'lattice_ready'",
            )
            patch_lattice(lattice=current_lattice)


async def main():
    monitor = Sender()
    task = asyncio.create_task(monitor.start())

    try:
        await task  # this will run forever
    except asyncio.CancelledError:
        monitor.stop()


if __name__ == "__main__":
    try:
        print("GONNA WAIT FOR SIGN!!")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped by user")
