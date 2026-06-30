"""
@author Tom Pacey
"""

import os
import io
import yaml
import numpy as np
from PIL import Image

import scipy.constants as const

from . import beam_to_screen as b2s

base_camera_array = {
    "pix_size_x": 25e-6,
    "pix_size_y": 25e-6,
    "central_pix_x": 1024,
    "central_pix_y": 1024,
    "n_pix_x": 2048,
    "n_pix_y": 2048,
}


class ScreenImage:
    def __init__(self, lattice_location):
        lattice_location = (
            lattice_location
            if lattice_location is not None
            else os.path.dirname(os.path.abspath(__file__))
        )
        with open(lattice_location + "/camera_arrays.yaml", "r") as settings_file:
            self.camera_arrays = yaml.load(
                settings_file.read().replace("\t", " "), Loader=yaml.Loader
            )
        with open(lattice_location + "/camera_conversions.yaml", "r") as settings_file:
            self.camera_conversions = yaml.load(
                settings_file.read().replace("\t", " "), Loader=yaml.Loader
            )
        with open(lattice_location + "/camera_assignments.yaml", "r") as settings_file:
            self.camera_assignments = yaml.load(
                settings_file.read().replace("\t", " "), Loader=yaml.Loader
            )
        self.camera_types = {}
        for k, v in self.camera_assignments.items():
            for s in v:
                self.camera_types[s] = k

    def get_screen_array(self, screen, myBeam):
        if screen in self.camera_types:
            if (
                self.camera_types[screen].lower() == "generic"
                or self.camera_types[screen].lower() == "basic"
            ):
                camera_array = base_camera_array
            else:
                camera_array = self.camera_arrays[self.camera_types[screen]]
        else:
            print(
                "Screen Missing from camera assignments:",
                screen,
                " - using generic camera!",
            )
            camera_array = base_camera_array
        return self.get_screen_result(screen, myBeam, **camera_array)

    def get_screen_result(
        self,
        screen,
        myBeam,
        n_pix_x=2560,
        n_pix_y=2160,
        pix_size_x=(5 * const.micro),
        pix_size_y=(5 * const.micro),
        central_pix_x=1500,
        central_pix_y=1000,
        base_constant=0,
        beam_pix_pad=250,
        physical_res=(5 * const.micro),
        KDE_method="fastKDE",
    ):
        screenDict = {}
        screenDict["n_pix_x"] = n_pix_x
        screenDict["n_pix_y"] = n_pix_y
        screenDict["pix_size_x"] = pix_size_x
        screenDict["pix_size_y"] = pix_size_y
        screenDict["central_pix_x"] = central_pix_x
        screenDict["central_pix_y"] = central_pix_y
        screenDict["base_constant"] = base_constant
        screenDict["beam_pix_pad"] = beam_pix_pad

        screenDict["physical_res"] = physical_res

        # Optional
        screenDict["KDE_method"] = KDE_method

        testScreen = b2s.BeamToScreen(screenDict, myBeam)
        # Do the digitisation
        bit_depth = 12
        peak_pix = 2**bit_depth
        testScreen.set_digitise_pix_by_max_value(
            bit_depth=bit_depth, max_pix_val=peak_pix
        )
        # saturation_charge_dens = np.max(testScreen.pix_vals_q_dens)

        output = io.BytesIO()
        img = Image.fromarray(
            np.uint8(testScreen.pix_vals_digitised / 4096 * 255), mode="L"
        )
        img.save(output, format="png")
        return img, output

    def load_image(self, filename):
        output = io.BytesIO()
        img = Image.open(filename, mode="r")
        img.save(output, format="png")
        return output
