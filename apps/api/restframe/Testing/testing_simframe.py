import io
import sys
import time
import h5py
import numpy as np
from typing import Union
from PIL import Image

sys.path.append("../../simframe")
sys.path.append("../API")
import data.SimFrame as sf


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
    # To hdf5
    FigArray = image_dict["arraydata"]
    name = image_dict["screen"]
    with h5py.File(filename, "w") as h5:
        create_image_dataset(h5, name, FigArray)


def figures_to_hdf5(image_dict_array, filename):
    with h5py.File(filename, "w") as h5:
        for image_dict in image_dict_array:
            FigArray = image_dict["arraydata"]
            if "arrayname" in image_dict:
                name = image_dict["arrayname"]
            else:
                name = image_dict["screen"]
            create_image_dataset(h5, name, FigArray)


class API:
    def initialise(self, **kwargs):
        self.simframe = sf.SimFrame_Interface(**kwargs)

    def get_master_lattice(self):
        return self.simframe.get_master_lattice()

    def get_lattice(self):
        return self.simframe.get_lattice()

    def load_settings(self, settings: str):
        return self.simframe.put_settings_filename(settings)

    def get_settings(self):
        return self.simframe.get_settings_filename()

    def set_ncpu(self, ncpu: str):
        return self.simframe.set_parallel_cpu_number(ncpu)

    def get_object(self, name: str, parameter: str = None):
        return self.simframe.put_object_properties(name, parameter, None)

    def modify_object(
        self, name: str, parameter: str, value: Union[str, float, int, bool]
    ):
        return self.simframe.put_object_properties(name, parameter, value)

    def track(self, end_lattice: str = "S07", **kwargs):
        return self.simframe.start_tracking(endfile=end_lattice, **kwargs)

    def track_and_wait(self, end_lattice: str = "S07", **kwargs):
        self.simframe.start_tracking(endfile=end_lattice, **kwargs)
        while not self.progress["finished_tracking"]:
            print(self.progress)
            time.sleep(0.1)

    @property
    def progress(self):
        return self.simframe.get_tracking_status()

    @property
    def get_twiss(self):
        return self.simframe.get_twiss()

    @property
    def get_screens(self):
        return self.simframe.get_screens()

    def get_screen_image(self, screenname):
        return self.simframe.get_screen_image(screenname)

    def get_screen_twiss(self, screenname):
        return self.simframe.get_screen_twiss(screenname)


def track_and_return_screen_image(screen, end_lattice):
    api.track_and_wait(end_lattice=end_lattice, rerun=True)
    return api.get_screen_image(screen)


def perform_quad_scan(
    quad, screen, start, stop, step, start_lattice=None, end_lattice=None
):
    filename = screen + ".hdf5"
    h5file = h5py.File(filename, "w")
    for value in np.arange(start, stop + step / 2, step):
        value = round(value, 2)
        print(api.modify_object(quad, "k1l", value))
        screenarray = track_and_return_screen_image(screen, end_lattice=end_lattice)
        FigArray = np.asarray(Image.open(io.BytesIO(screenarray)))
        arrayname = quad + "=" + str(round(value, 2))
        create_image_dataset(h5file, arrayname, FigArray)


def perform_solenoid_scan(
    solenoid, screen, start, stop, step, start_lattice=None, end_lattice=None
):
    filename = screen + ".hdf5"
    h5file = h5py.File(filename, "w")
    for value in np.arange(start, stop + step / 2, step):
        value = round(value, 2)
        print(api.modify_object(solenoid, "field_amplitude", value))
        screenarray = track_and_return_screen_image(screen, end_lattice=end_lattice)
        FigArray = np.asarray(Image.open(io.BytesIO(screenarray)))
        arrayname = solenoid + "=" + str(round(value, 2))
        create_image_dataset(h5file, arrayname, FigArray)


def perform_corrector_scan(
    corrector, screen, start, stop, step, start_lattice=None, end_lattice=None
):
    filename = "CORR_" + screen + ".hdf5"
    api.modify_object("CLA-L01-CAV-SOL-01", "field_amplitude", 0.12)
    h5file = h5py.File(filename, "w")
    for hvalue in np.arange(start, stop + step / 2, step):
        hvalue = round(hvalue, 7)
        print(api.modify_object(corrector, "horizontal_kick", hvalue))
        for vvalue in np.arange(start, stop + step / 2, step):
            vvalue = round(vvalue, 7)
            print(api.modify_object(corrector, "vertical_kick", vvalue))
            screenarray = track_and_return_screen_image(screen, end_lattice=end_lattice)
            FigArray = np.asarray(Image.open(io.BytesIO(screenarray)))
            arrayname = "h=" + str(hvalue) + ", v=" + str(vvalue)
            create_image_dataset(h5file, arrayname, FigArray)
    h5file.close()


if __name__ == "__main__":
    start = time.time()
    api = API()
    api.initialise(
        clean=False,
        runs_directory="../API/Output/ISIS/",
        settings_file="../API/Lattices/ISIS/MEBT/ISIS_MEBT.def",
        master_lattice="../API/Lattices/ISIS/MEBT/input/",
        screen_directory="../API/Lattices/ISIS/MEBT/screens/",
        particle="proton",
    )
    print("initialise", time.time() - start)
    api.track_and_wait()
    print("track and wait", time.time() - start)
    lattice = api.get_lattice()
    print(lattice.sections["MEBT"].beam_summary)
    exit()
    base_image = lattice.sections["LEBT"].screens[0].camera.arraydata
    print("get_lattice", time.time() - start)
    api.simframe.set_lattice_elements(lattice)
    print("set lattice elements", time.time() - start)
    # api.modify_object("CLA-S06-MAG-QUAD-01", "k1l", 0.3)
    # api.track_and_wait()
    # print('track and wait', time.time() - start)
    # lattice = api.get_lattice()
    # print('get_lattice', time.time() - start)
    # new_image = lattice.sections['S07'].screens[0].camera.arraydata
    # print(base_image == new_image)
    exit()
    api.modify_object("generator", "number_of_particles", 2 ** (3 * 3))
    api.modify_object("CLA-S06-MAG-QUAD-01", "k1l", 0.2)
    screen = "CLA-S07-DIA-SCR-05"
    # # with h5py.File('test.hdf5', 'w') as h5:
    # print('Track 1')
    api.track_and_wait()
    screentwiss = api.get_screen_twiss(screen)
    print(screentwiss)
    exit()
    # # FigArray = screenarray['arraydata']
    # # create_image_dataset(h5, 'track 1', FigArray)
    #
    # print('Track 2')
    # api.track_and_wait()
    # # screenarray = api.get_screen(screen)
    # # FigArray = screenarray['arraydata']
    # # create_image_dataset(h5, 'track 2', FigArray)
    # api.modify_object('CLA-S06-MAG-QUAD-01', 'k1l', -0.1)
    # print('Track 3 - change quad-02')
    # api.track_and_wait()
    # # screenarray = api.get_screen(screen)
    # # FigArray = screenarray['arraydata']
    # # # create_image_dataset(h5, 'track 3', FigArray)
    # # #
    #
    # api.modify_object('CLA-S06-MAG-QUAD-01', 'k1l', 0.1)
    # print('Track 4 - reset quad-02 same as Track 1')
    # api.track_and_wait()
    # # screenarray = api.get_screen(screen)
    # # FigArray = screenarray['arraydata']
    # # create_image_dataset(h5, 'track 4', FigArray)
    # #
    # api.modify_object('CLA-S07-MAG-QUAD-01', 'k1l', -0.1)
    # print('Track 5 - change S07 quad-01 - should prefix!')
    # api.track_and_wait()
    # # screenarray = api.get_screen(screen)
    # # FigArray = screenarray['arraydata']
    # # create_image_dataset(h5, 'track 5', FigArray)
    # exit()
    print(api.modify_object("generator", "number_of_particles", 2 ** (3 * 5)))
    print(api.set_ncpu(8))
    # perform_quad_scan('CLA-S07-MAG-QUAD-01','CLA-S07-DIA-SCR-01', -1, 1, 1, start_lattice='S07', end_lattice='S07')
    # perform_solenoid_scan('CLA-L01-CAV-SOL-01','CLA-S02-DIA-SCR-03', 0.0, 0.3, 0.03, start_lattice='L01', end_lattice='L02')
    perform_corrector_scan(
        "CLA-S02-MAG-HVCOR-01",
        "CLA-S03-DIA-SCR-01",
        -0.75e-3,
        1e-3,
        0.25e-3,
        start_lattice="S02",
        end_lattice="S03",
    )
