import os, sys, io
import h5py

sys.path.append("..\..\simframe")
import SimulationFramework.Framework as fw
import SimulationFramework.Modules.Beams as rbf
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvas
from testing import API, create_image_dataset

uuid = "630512b1-b871-436d-9de7-46104febb67f"

api = API()
print(api.initialise(uuid="630512b1-b871-436d-9de7-46104febb67f", clean=False))
screennames = [scr for scr in api.get_screens["screens"] if "-SCR-" in scr]
print("screennames:", screennames)
with h5py.File("test.hdf5", "w") as h5:
    for scr in screennames:
        print("\t", scr)
        image_dict = api.get_screen(scr)
        FigArray = image_dict["screen_data"]
        name = image_dict["screen"]
        create_image_dataset(h5, name, FigArray)
# figures_to_hdf5(screenData, 'test.hdf5')
