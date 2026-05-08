import os, sys, io
import h5py
import yaml

sys.path.append("../../simframe")
sys.path.append("../../ADI_SADI")
sys.path.append("../Examples")

import SimulationFramework.Framework as fw
import SimulationFramework.Modules.Beams as rbf
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvas
from testing import API, figure_to_hdf5
from screen_image import get_screen_result


framework_directory_instances = {}
uuid = "630512b1-b871-436d-9de7-46104febb67f"
framework_directory_instances[uuid] = fw.frameworkDirectory(
    "../Examples/runs/" + uuid, beams=True
)

screen = "CLA-S01-DIA-SCR-01"
camera = screenFactory.getScreen(screen)["camera_name"]
camera_array = get_camera_array(camera)
print(camera, ":", camera_array)
screenData = get_screen_result(
    framework_directory_instances[uuid].getScreen(screen), **camera_array
)
figure_to_hdf5(screenData, screen + ".hdf5")
