import io
import sys
import os
import time
import requests
import json
import yaml
import h5py
import numpy as np
from typing import Union
from local_API import API
from PIL import Image

sys.path.append("../API")
# from data.HardwareFactory import FakeHardwareFactory

# factory = FakeHardwareFactory()
# cameraFactory = factory.getCameraFactory(
#     base_folder=r"\\claraserv3.dl.ac.uk\claranet\packages\CATAP\Nightly\CATAP_Nightly_07_02_2023\python38\MasterLattice"
# )
# screenFactory = factory.getScreenFactory(
#     base_folder=r"\\claraserv3.dl.ac.uk\claranet\packages\CATAP\Nightly\CATAP_Nightly_07_02_2023\python38\MasterLattice"
# )
with open("../API/data/camera_conversions.yaml", "r") as settings_file:
    camera_conversions = yaml.load(
        settings_file.read().replace("\t", " "), Loader=yaml.Loader
    )


def create_image_dataset(h5, name, FigArray):
    ImageDataset = h5.create_dataset(
        name=name,
        data=FigArray,
        dtype="uint8",
        chunks=True,
        compression="gzip",
        compression_opts=9,
    )
    ImageDataset.attrs["CLASS"] = np.string_("IMAGE")
    ImageDataset.attrs["IMAGE_VERSION"] = np.string_("1.2")
    ImageDataset.attrs["IMAGE_SUBCLASS"] = np.string_("IMAGE_GRAYSCALE")
    ImageDataset.attrs["INTERLACE_MODE"] = np.string_("INTERLACE_MODE")
    ImageDataset.attrs["IMAGE_MINMAXRANGE"] = np.uint8(255)


def figure_to_hdf5(image_dict, filename):
    ## To hdf5
    FigArray = image_dict["arraydata"]
    name = image_dict["screen"]
    with h5py.File(filename, "w") as h5:
        create_image_dataset(h5, name, FigArray)


def figures_to_hdf5(image_dict_array, filename):
    with h5py.File(filename, "w") as h5:
        for image_dict in image_dict_array:
            FigArray = image_dict["screen_data"]
            name = image_dict["screen"]
            create_image_dataset(h5, name, FigArray)


def track_and_return_screen(screen, end_lattice):
    api.track_and_wait(end_lattice=end_lattice, rerun=True)
    return api.get_screen_image(screen)


def perform_quad_scan(quad, screen, start, stop, step, end_lattice="S07"):
    screenData = []
    filename = screen + ".hdf5"
    with h5py.File(filename, "w") as h5:
        for value in np.arange(start, stop + step / 2, step):
            value = round(value, 2)
            print(api.modify_object(quad, "k1l", np.around(value, decimals=3)))
            screenarray = track_and_return_screen(screen, end_lattice=end_lattice)
            FigArray = np.asarray(Image.open(io.BytesIO(screenarray.content)))
            # print(FigArray[0])
            arrayname = quad + "=" + str(round(value, 2))
            create_image_dataset(h5, arrayname, FigArray)


def perform_solenoid_scan(
    solenoid, screen, start, stop, step, start_lattice=None, end_lattice=None
):
    screenData = []
    filename = screen + ".hdf5"
    with h5py.File(filename, "w") as h5:
        for value in np.arange(start, stop + step / 2, step):
            value = round(value, 2)
            print(api.modify_object(solenoid, "field_amplitude", value))
            screenarray = track_and_return_screen(screen, end_lattice=end_lattice)
            FigArray = np.asarray(Image.open(io.BytesIO(screenarray.content)))
            arrayname = solenoid + "=" + str(round(value, 2))
            create_image_dataset(h5, arrayname, FigArray)


def perform_corrector_scan(
    corrector, screen, start, stop, step, start_lattice=None, end_lattice=None
):
    screenData = []
    filename = "CORR_" + screen + ".hdf5"
    api.modify_object("CLA-L01-CAV-SOL-01", "field_amplitude", 0.15)
    with h5py.File(filename, "w") as h5:
        for value in np.arange(start, stop + step / 2, step):
            value = round(value, 2)
            print(api.modify_object(corrector, "horizontal_kick", value))
            screenarray = track_and_return_screen(screen, end_lattice=end_lattice)
            FigArray = np.asarray(Image.open(io.BytesIO(screenarray.content)))
            arrayname = corrector + "=" + str(round(value, 2))
            create_image_dataset(h5, arrayname, FigArray)


def perform_HV_corrector_scan(
    corrector, screen, start, stop, step, start_lattice=None, end_lattice=None
):
    screenData = []
    filename = "CORR_" + screen + ".hdf5"
    api.modify_object("CLA-L01-CAV-SOL-01", "field_amplitude", 0.12)
    h5file = h5py.File(filename, "w")
    for hvalue in np.arange(start, stop + step / 2, step):
        hvalue = round(hvalue, 6)
        print(api.modify_object(corrector, "horizontal_kick", hvalue))
        for vvalue in np.arange(start, stop + step / 2, step):
            vvalue = round(vvalue, 6)
            print(api.modify_object(corrector, "vertical_kick", vvalue))
            screenarray = track_and_return_screen(screen, end_lattice=end_lattice)
            FigArray = np.asarray(Image.open(io.BytesIO(screenarray.content)))
            arrayname = "h=" + str(hvalue) + ", v=" + str(vvalue)
            create_image_dataset(h5file, arrayname, FigArray)
    h5file.close()


if __name__ == "__main__":
    api = API(host="http://127.0.0.1", port=8000)
    # api = API(host='http://apclara2.dl.ac.uk', port=8001)
    api.initialise(clean=False)
    # api.set_ncpu(12)
    # api.modify_object('generator','number_of_particles', 2**(3*5))
    progress = api.track_and_wait(end_lattice="S07", rerun=False)
    print(api.get_master_lattice())
    exit()
    print(api.get_magnet_momenta())
    # exit()
    print(progress)
    print(api.get_magnet_momenta())
    print(api.get_screens)
    print(
        np.asarray(
            Image.open(
                io.BytesIO(
                    api.get_screen_image("CLA-S07-DIA-SCR-01", force=True).content
                )
            )
        )
    )
    for scr in api.get_screens["screens"]:
        print(scr)
        print(api.get_screen_image(scr))
        print(api.get_screen_image(scr))
    # perform_quad_scan('CLA-S07-MAG-QUAD-01','CLA-S07-DIA-SCR-01', -1, 1, 0.1)
    # perform_solenoid_scan('CLA-L01-CAV-SOL-01','CLA-S02-DIA-SCR-03', 0.0, 0.3, 0.03, start_lattice='L01', end_lattice='L02')
    # perform_corrector_scan('CLA-S02-MAG-HVCOR-01','CLA-S03-DIA-SCR-01', -0.75e-3, 1e-3, 0.25e-3, start_lattice='S02', end_lattice='S03')
