from janus_common.utils.restframe_simple import API
from janus_common.utils import comms_handler

restframe = API()
lattice = restframe.get_lattice()
comms_handler.add_lattice(lattice)
