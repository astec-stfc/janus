from p4p.client.thread import Context

ctx = Context("pva")

ctx.put("VM-Linac:INITIAL-CONDITIONS:BETA_X", 12.0, throw=False)
ctx.put("VM-Linac:INITIAL-CONDITIONS:BETA_Y", 12.0, throw=False)
ctx.put("VM-Linac:INITIAL-CONDITIONS:NEMIT_X", 1e-6, throw=False)
ctx.put("VM-Linac:INITIAL-CONDITIONS:NEMIT_Y", 1e-6, throw=False)
ctx.put("VM-INITIAL-CONDITIONS:ENABLE", "Linac", throw=False)