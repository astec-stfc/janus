from p4p.client.thread import Context
from epics import caput
ctx = Context("pva")
ctx.put("VM-GENERATOR:ENABLE", 1)
ctx.put("VM-GENERATOR:NUMBER_OF_PARTICLES", 32768*2)
caput("VM-CLA-S02-MAG-QUAD-01:CalcK", 10.2)