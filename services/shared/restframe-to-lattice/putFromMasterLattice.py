"""Legacy helper for pushing a lattice from RestFrame to lattice-api.

This script still exercises the schema/JSON path. The main tracked-results flow
now prefers binary pass-through via lattice-to-restframe and /v1/lattice/binary.
"""

from janus_common.utils.restframe_simple import API
from janus_common.utils import comms_handler

restframe = API()
lattice = restframe.get_lattice()
comms_handler.add_lattice(lattice)
