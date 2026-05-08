import sys, os, time

sys.path.append("../API")
sys.path.append("../../simframe")
sys.path.append("../../SimFrame_Examples")
sys.path.append("../../ADI_SADI")
sys.path.append("../../clara-control-room-applications")

import uuid
import yaml
from typing import Optional
from sqlmodel import Session
from database.tables import Lattice, Run
from main import create_uuid, get_existing_uuids

import SimulationFramework.Framework as fw
from framework_test import astra_track, elegant_track

from database.database_creator import DatabaseCreator
from database.database_writer import DatabaseWriter

db = DatabaseCreator()
db.create_db_and_tables()
db_writer = DatabaseWriter(engine=db.engine)

# astra_track(scaling=3)
# elegant_track()
framework = fw.Framework("example_elegant", clean=False, verbose=True)
framework.loadSettings("Lattices/clara400_v12_v3.def")
framework.change_Lattice_Code("All", "elegant", exclude=["generator", "injector400"])
framework.set_lattice_prefix("S02", "../example_ASTRA/")

print(list(framework.getElementType("quadrupole", ["objectName", "k1l"])))
exit()

print(framework["generator"].save_lattice())
# for line in framework.lines:
#     print(framework.save_lattice(lattice=line, dictionary=True))

# db_writer.save_dict_to_db(settings_dict_to_save)
