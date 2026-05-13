from common.restframe_simple import API
from common import comms_handler

restframe = API()
lattice = restframe.get_lattice()
comms_handler.add_lattice(lattice)
