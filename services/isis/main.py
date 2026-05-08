import time
import asyncio
from datetime import datetime
from schemas import elements
from schemas.elements import Lattice, Magnet, MagnetEnum, Cavity
from random import random
from p4p.client.asyncio import Context
from common.kafka_restframe import API
from common.comms_handler import patch_lattice,get_lattice

        

class Sender(API):
    def __init__(self):
        super().__init__(group_id = "isis_to_comm")
        self._pv_to_check = "ISIS:SIM:SEED" # TODO This is where we will add all the IOCs
        self._ctx = Context("pva")
        self._current_value = None#self._ctx.get(self._pv_to_check)
        
        self.out_topic="com_rest_lattice"
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

    # def has_lattice_changed(self) -> bool:
    #     """This is where you would compare the current lattice with the epics settings"""
   
    #     _changed = self._ctx.get(self._pv_to_check) != self._current_value
  
    #     if _changed:
    #         self._current_value = self._ctx.get(self._pv_to_check)
    #     return _changed

    async def has_sim_seed_updated(self) -> bool:
        """This is where you would compare the current lattice with the epics settings"""
        try:
            _value = await asyncio.wait_for(self._ctx.get(self._pv_to_check), timeout=10)
        except TimeoutError as e:
            print(f"Timeout while getting value for {self._pv_to_check}: {str(e)}")
            return False    
        else:
            _changed = _value != self._current_value
            if _changed:
                self._current_value = _value
                # value = self._ctx.get(self._pv_to_check, throw=False)
            return _changed

    async def initialise_all_sim_codes(self, lattice: Lattice) -> None:
        for section in lattice.sections.values():
            if section.model:
                try:
                    await asyncio.wait_for(
                        self._ctx.put(
                            f"VM-{section.name}-SIMULATION:CODE",
                            section.model,
                        ),
                        timeout=10
                    )
                except TimeoutError as e:
                    print(f"Timeout while setting SIMULATION:CODE for {section.name}: {str(e)}")
                    continue

    async def set_sim_codes_from_epics(self, lattice: Lattice):
        for section in lattice.sections.values():
            # get the sim code from epics
            try:
                epics_sim_code = await asyncio.wait_for(
                    self._ctx.get(f"VM-{section.name}-SIMULATION:CODE"),
                    timeout=10
                )
            except TimeoutError as e:
                print(f"Timeout while getting SIMULATION:CODE for {section.name}: {str(e)}")
                continue
            if epics_sim_code != "undefined":
                # once we know it has a real value, check if it has changed
                if section.model != epics_sim_code:
                    # set the model for the section to the new code
                    section.model = epics_sim_code
        return lattice

    async def has_lattice_changed(self, lattice: elements.Lattice) -> bool:
        lattice_with_changes_from_epics = await self.set_sim_codes_from_epics(lattice)
        return get_lattice() != lattice_with_changes_from_epics


    
    async def start(self):
        self.sub = self._ctx.monitor(self._pv_to_check, self.on_epics_update)
        while True:
            await asyncio.sleep(3600)

    async def on_epics_update(self,value):
        print(f"Received update for {self._pv_to_check}: {value}")
        current_lattice = get_lattice()# This gets you the latest lattice available, I think dunno, if you use self.get_lattice it uses the restframe API and you get screwed, that is on me, I could change it but I am a simple man

        # new_val = await self._ctx.get(self._pv_to_check) 
        if self.counter:
            print("FIRST RUN, JUST SENDING LATTICE TO COMMS WITHOUT CHECKING FOR CHANGES")
            self.counter = False
            return
        if await self.has_sim_seed_updated():
            print("SIM SEED UPDATED, RANDOMISING LATTICE")
            self._randomise_lattice(lattice=current_lattice)

        if await self.has_lattice_changed(current_lattice):
            print("LATTICE SETTINGS CHANGED, SENDING UPDATED LATTICE TO COMMS")
            print("SENDING DATA OVER NOW")
            patch_lattice(lattice=current_lattice)
            uuid_to_be_sent = current_lattice.uuid
            print("UUID: ",uuid_to_be_sent)
    
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


