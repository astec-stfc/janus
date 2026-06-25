import os
from copy import deepcopy
from typing import List, Dict
from pydantic import BaseModel, create_model, validator  # type: ignore
import hashlib
import json
import yaml
import sys

sys.path.append("../../")
from janus_common.schemas.elements import (
    Element,
    Screen,
    Camera,
    Lattice,
    Section,
    Magnet,
    MagnetEnum,
    BPM,
    Cavity,
    CavityEnum,
    Marker,
    Generator,
)


def save_data_json(filename, savedict):
    with open(filename, "w") as json_file:
        json.dump(savedict, json_file)


def load_data_json(filename, dataclass):
    if os.path.isfile(filename):
        with open(filename, "r") as json_file:
            dataclass.parse_file(json_file)


def save_data_yaml(filename, savedict):
    with open(filename, "w") as yaml_file:
        yaml.dump(savedict, yaml_file, default_flow_style=True)


def load_data_yaml(filename, dataclass):
    if os.path.isfile(filename):
        with open(filename, "r") as yaml_file:
            savedict = yaml.full_load(yaml_file)
            dataclass.parse_obj(savedict)


def hash_function(data):
    return hashlib.md5(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()

sf_mapping = {
    "beam_position_monitor": {"type": BPM},
    "screen": {"type": Screen, "camera": Camera},
    "marker": {"type": Marker},
    "quadrupole": {
        "type": Magnet,
        "subtype": MagnetEnum.quadrupole,
        "KnL": [None, "k1l", None, None],
        "gradient": "gradient",
    },
    "dipole": {
        "type": Magnet,
        "subtype": MagnetEnum.dipole,
        "KnL": ["angle", None, None, None],
    },
    "sextupole": {
        "type": Magnet,
        "subtype": MagnetEnum.sextupole,
        "KnL": [None, None, "k2l", None],
    },
    "corrector": {
        "type": Magnet,
        "subtype": MagnetEnum.corrector,
        "KnL": ["angle", None, None, None],
    },
    "solenoid": {
        "type": Magnet,
        "subtype": MagnetEnum.solenoid,
        "KnL": [None, None, None, None],
        "field_amplitude": None,
    },
    "rfcavity": {
        "type": Cavity,
        "subtype": CavityEnum.linac,
        "field_amplitude": None,
        # "gradient": None,
        "phase": None,
        "crest": None,
    },
    "rfdeflectingcavity": {
        "type": Cavity,
        "subtype": CavityEnum.deflecting,
        "field_amplitude": None,
        # "gradient": None,
        "phase": None,
        "crest": None,
    },
}
twiss_mapping = {"emit_x": "ex", "emit_y": "ey", "nemit_x": "enx", "nemit_y": "eny"}
centroid_values = ["x", "y"]
sigma_values = ["x", "y", "t", "cp"]
covariance_values = {
    "xx": ["x", "x"],
    "xxp": ["x", "xp"],
    "yy": ["y", "y"],
    "yyp": ["y", "yp"],
    "xy": ["x", "y"],
    "xyp": ["x", "xp"],
    "yxp": ["y", "xp"],
}
sigfig = 5


class ChangesLattice(BaseModel):
    name: str
    hash: str | None = None

    def __eq__(self, other):
        if not isinstance(other, ChangesLattice):
            return NotImplemented
        return self.hash == other.hash


class ScreenElement(BaseModel):
    screen: str
    arraydata: str | None = None
    updated: bool = False


class ScreenLattice(BaseModel):
    uuid: str | None = None
    screens: List[Screen]


def RESTData(latticeObjects_names):
    # RESTData is a factory function (despite the PascalCase name) — not a class.
    # Calling it once initialises all the data-model classes for a specific set of
    # accelerator lattice sections (e.g. ["injector", "linac", "dogleg"]).
    # The resulting classes are pushed into module-level globals so that the rest of
    # the API can import them without needing to pass the lattice list everywhere.

    #  _Class_	                    _Purpose_
    # ChangesData	                Fingerprints a simulation run by hashing the config of every lattice section. 
    #                               Two runs are equal iff all their section hashes match.
    # ChangesClass	                Registry of ChangesData entries keyed by UUID. 
    #                               Core job: find_prefix_entry — given a new run's config, find the prior run that 
    #                               shares the longest matching prefix of sections so those sections' outputs can be 
    #                               reused without re-simulating.
    # PrefixData / PrefixesClass	Tracks which run UUID "owns" the output files for each section. 
    #                               When sections are reused from a prior run, they keep the old UUID as their 
    #                               prefix; only changed sections get the new UUID.
    # LatticeClass	                The full in-memory accelerator model for one run — one Section (or Generator) 
    #                               per lattice, populated with all elements. 
    #                               Provides helpers to navigate elements by name, type, or section, and to 
    #                               serialise the whole thing into the Lattice API schema.

    # Expose the generated classes and shared state as module globals so callers can
    # do `from data import ChangesClass` after calling RESTData() once at startup.
    global ChangesData, ChangesClass, PrefixesClass, LatticeClass, lattice_names, lattices, PrefixData

    # Store the ordered list of lattice section names used to build every model below.
    # Order matters: lattices are run sequentially (injector → linac → …) and the
    # prefix-reuse logic depends on this ordering.
    lattice_names = latticeObjects_names

    # ── ChangesDataBase ────────────────────────────────────────────────────────────
    # Build a Pydantic model whose fields include one optional ChangesLattice entry
    # per lattice section. This captures a "snapshot" of which lattice configurations
    # were active for a given simulation run so we can detect duplicates later.
    # Each field defaults to None (no data yet for that lattice section).
    lattices = {lat: (ChangesLattice | None, None) for lat in lattice_names}

    # create_model() generates a Pydantic BaseModel at runtime with the fields we
    # just built, plus a uuid (required), an optional prefix string, and a hash.
    ChangesDataBase = create_model(
        "ChangesData",
        uuid=(str, ...),           # Required unique run identifier (UUID string).
        prefix=(str | None, None), # Optional filesystem prefix string for this run.
        **lattices,                # One optional ChangesLattice field per lattice.
        hash=(str | None, None)    # MD5 fingerprint computed by the validator below.,
    )

    class ChangesData(ChangesDataBase):
        # ChangesData extends the dynamic base to add hashing and comparison logic.
        # An instance represents the full lattice configuration fingerprint for one
        # simulation run: which magnet/cavity/screen settings were active per section.

        @validator("hash", always=True)
        def create_changes_hash(cls, value, values):
            # Pydantic calls this validator whenever a ChangesData instance is
            # created or updated. `values` contains all already-validated fields,
            # i.e. all the per-lattice ChangesLattice entries.
            # We ignore any incoming `value` for hash and always recompute it, so
            # the hash is always consistent with the current lattice state.

            # Collect the dict representation of every non-None lattice entry in
            # order. Lattices that haven't been set yet (None) are skipped so a
            # partially-filled run still gets a meaningful hash.
            full = [
                values[lat].dict()
                for lat in lattice_names
                if lat in values and values[lat] is not None
            ]
            # Produce a stable MD5 over the sorted JSON of all lattice dicts.
            # sort_keys=True in hash_function ensures field ordering doesn't affect
            # the hash, making it purely content-addressable.
            return hash_function(full)

        def compare_lattices(self, other):
            # Returns a {lattice_name: bool} dict showing which individual lattice
            # sections are identical between self and other.
            # Used by find_prefix_entry to identify the longest matching prefix so
            # that unchanged upstream lattices can be reused from a previous run.
            if not isinstance(other, ChangesData):
                return NotImplemented
            return {
                lat: getattr(self, lat) == getattr(other, lat) for lat in lattice_names
            }
            # Equality of ChangesLattice entries is defined by their hash field
            # (see ChangesLattice.__eq__ above), so this compares config hashes
            # per section, not object identity.

        def __eq__(self, other):
            # Two ChangesData snapshots are equal only if every lattice section
            # matches. This is used by run_exists() to detect a fully identical
            # previous run (so we can return cached results without re-simulating).
            if not isinstance(other, ChangesData):
                return NotImplemented
            return all(self.compare_lattices(other).values())

        def __neq__(self, other):
            if not isinstance(other, ChangesData):
                return NotImplemented
            return not all(self.compare_lattices(other).values())

    # ── ChangesClass ──────────────────────────────────────────────────────────────
    class ChangesClass:
        # A registry (dictionary) of ChangesData entries keyed by run UUID.
        # Persisted across requests so the API can answer "has this exact
        # lattice configuration been simulated before?" without re-running the code.
        base_class = ChangesData  # Allows PrefixesClass to inherit and swap this.

        def __init__(self, runs_directory):
            self._dictionary = {}               # uuid → ChangesData
            self._runs_directory = runs_directory  # Root dir where run subdirs live.

        def dict(self):
            # Serialise entire registry to a plain dict (for JSON persistence).
            return {k: v.dict() for k, v in self._dictionary.items()}

        def json(self):
            # Serialise entire registry to a JSON string.
            return json.dumps({k: v.json() for k, v in self._dictionary.items()})

        def parse_obj(self, obj):
            # Deserialise a plain dict back into the registry (e.g. loading from disk).
            for k, v in obj.items():
                self.add_entry(uuid=k, entry=self.base_class.parse_obj(v))

        def get_keys(self):
            # Return all run UUIDs currently in the registry.
            return list(self._dictionary.keys())

        def get_keys_hashes(self):
            # Return {uuid: hash} for every registered run — cheap way to scan
            # for duplicates without deserialising full ChangesData objects.
            return {k: self._dictionary[k].hash for k in self._dictionary.keys()}

        def add_entry(self, uuid: str, entry: ChangesData):
            # Register a new run's configuration snapshot.
            self._dictionary[uuid] = entry

        def get_uuid(self, uuid: str) -> ChangesData | None:
            # Look up a run by its UUID, or None if not registered.
            return self._dictionary.get(uuid)

        def count_trues(self, true_list: list):
            # Given an ordered list of booleans (one per lattice section, in
            # simulation order), return the index of the first False.
            # This tells us how many leading lattice sections are shared with a
            # previous run — i.e. how far into the pipeline we can skip re-running.
            # If all are True (no False found), returns len(list) meaning every
            # section is reusable.
            true_list = (
                list(true_list) if not isinstance(true_list, list) else true_list
            )
            try:
                return true_list.index(False)
            except ValueError:
                return len(true_list)

        def run_exists(self, other: ChangesData):
            # Returns True if any registered run has an identical hash AND its
            # output directory still exists on disk. Both conditions are required:
            # a matching hash with a missing directory means we must re-run.
            return (
                any(self.compare_entries(other).values())
                if len(self._dictionary) > 0
                else False
            )

        def find_prefix_entry(self, other: ChangesData):
            # Core optimisation: find the previously-run simulation that shares the
            # longest common prefix of lattice sections with `other`.
            # If sections [0..n-1] are identical to a prior run, we can reuse its
            # output files for those sections and only re-simulate from section n.
            # Returns (uuid, start_lattice_name, start_lattice_index).
            null_result = None, lattice_names[0], 0  # Fall-through: re-run everything.

            if len(self._dictionary) > 0:
                lattice_matches = {}
                for uuid, change in self._dictionary.items():
                    if self.uuid_directory_exists(uuid):
                        # Count how many leading sections this prior run shares with `other`.
                        # count_trues returns the index of the first mismatch,
                        # so higher = more sections can be reused.
                        lattice_matches[uuid] = self.count_trues(
                            change.compare_lattices(other).values()
                        )
                    else:
                        # The directory for this run is gone; treat as no match.
                        lattice_matches[uuid] = 0

                most_trues = list(lattice_matches.values())

                # Pick the prior run with the highest number of matching leading sections.
                idx_most_trues = most_trues.index(max(most_trues))

                # result = [uuid_of_best_match, count_of_matching_leading_sections]
                result = list(list(lattice_matches.items())[idx_most_trues])

                # idx_start_lattice is the count of matching sections, which is also
                # the index into lattice_names where we need to start re-simulating.
                idx_start_lattice = result[1]
                print(f"{idx_start_lattice=}")

                if idx_start_lattice < 1:
                    # Zero leading sections match → we must re-run from the beginning.
                    return null_result
                else:
                    if idx_start_lattice < len(lattice_names):
                        # Start re-simulation at this lattice section index.
                        start_lattice = lattice_names[idx_start_lattice]
                    else:
                        # All sections matched; start from the last one (shouldn't
                        # normally reach here because run_exists would catch a full match).
                        start_lattice = lattice_names[-1]
                return result[0], start_lattice, idx_start_lattice
            return null_result

        def uuid_directory_exists(self, uuid: str) -> bool:
            # Check that the output directory for a given run UUID still exists.
            # A registered run whose directory was deleted is considered invalid.
            return os.path.isdir(os.path.join(self._runs_directory, str(uuid)))

        def compare_entries(self, other: ChangesData):
            # Returns {uuid: bool} where True means that run's hash matches `other`
            # AND its output directory exists. Used by run_exists() to confirm a
            # cached result is actually available on disk.
            return {
                uuid: other.hash == entry.hash and self.uuid_directory_exists(uuid)
                for uuid, entry in self._dictionary.items()
            }

        def get_entry(self, other: ChangesData) -> list | tuple | None:
            # Return (uuid, ChangesData) for the first registered run whose hash
            # matches `other`, or None if not found.
            # Used to retrieve the UUID of an already-computed identical run.
            for uuid, entry in self._dictionary.items():
                if entry.hash == other.hash:
                    return uuid, entry
                    break  # unreachable after return, but kept for clarity
            return None

    # ── PrefixData & PrefixesClass ────────────────────────────────────────────────
    # Each simulation run writes output files namespaced by a "prefix" (UUID string).
    # When sections are reused from a previous run, those sections keep the OLD run's
    # UUID as their prefix while only the changed sections use the new UUID.
    # PrefixData records this per-section prefix mapping for each run.

    prefixes = {lat: (str, None) for lat in lattice_names}  # Optional str per lattice.
    PrefixData = create_model("PrefixData", uuid=(str, ...), **prefixes)

    class PrefixesClass(ChangesClass):
        # Extends ChangesClass to manage prefix (UUID per lattice section) records
        # alongside the change-detection records in ChangesClass.
        base_class = PrefixData

        def get_prefixes(self, uuid: str) -> dict:
            # Return {lattice_name: prefix_uuid} for every section of a given run.
            # The prefix_uuid for a section is the UUID of whichever prior run produced
            # the output files for that section (may differ from the current run's UUID
            # if the section was reused).
            prefix = self.get_uuid(uuid)
            return {lattice: getattr(prefix, lattice) for lattice in lattice_names}

        def add_entry(self, uuid: str, entry: PrefixData) -> None:  # type: ignore
            # Register prefix data for a new run. Any lattice section whose prefix is
            # still None gets the current run's UUID assigned — meaning that section
            # is "owned" by this run (not reused from a prior one).
            for lattice in lattice_names:
                if getattr(entry, lattice) is None:
                    setattr(entry, lattice, uuid)
            self._dictionary[uuid] = entry

        def get_entry(self, settings: PrefixData) -> list | None:  # type: ignore
            # Find and return the PrefixData that matches `settings` by equality.
            for uuid, entry in self._dictionary.items():
                if entry == settings:
                    return entry
                    break  # unreachable after return

        def copy_prefixes(self, original_uuid: str, prefixIndex: int, new_uuid: str):
            # Create a new PrefixData for `new_uuid` by copying the prefix assignments
            # from `original_uuid`, then replacing every section from `prefixIndex+1`
            # onwards with `new_uuid`.
            #
            # Example: lattice_names = ["injector", "linac", "dogleg"]
            #   original_uuid = "abc", prefixIndex = 1, new_uuid = "xyz"
            #   Result: injector → "abc" (reused), linac → "abc" (reused),
            #           dogleg → "xyz" (re-run with new prefix)
            set2 = deepcopy(self.get_uuid(original_uuid))  # Copy all existing prefixes.
            set2.uuid = new_uuid  # type: ignore                # Assign the new run's UUID.
            for lattice in lattice_names[prefixIndex + 1 :]:
                # Override sections after the fork point with the new run's UUID so
                # they write fresh output files rather than overwriting the original.
                setattr(set2, lattice, new_uuid)
            return set2

    # ── LatticeData & LatticeClass ────────────────────────────────────────────────
    # LatticeClass is the main in-memory representation of the full accelerator model
    # for one simulation run. It holds one Section (or Generator) per lattice section,
    # each populated with the full element list (magnets, screens, BPMs, cavities…).

    lattices = {}
    for lat in lattice_names:
        if lat == "generator":
            # The particle generator (gun/laser/injector source) uses the Generator
            # schema, which has different fields from a beamline Section.
            lattices.update({lat: (Generator, ...)})
        else:
            # Every other beamline section uses the Section schema, which contains
            # lists of screens, BPMs, magnets, cavities, etc.
            lattices.update({lat: (Section, ...)})

    # Dynamically create a Pydantic model with one required field per lattice section.
    LatticeData = create_model("LatticeData", **lattices)

    class LatticeClass(LatticeData):
        # Extends the dynamic LatticeData model with helper methods for navigating
        # and mutating the multi-section accelerator model.

        def set_lattice_prefix(self, lattice: str, prefix: str):
            # Stamp the given prefix UUID onto a lattice section's uuid field.
            # This links the in-memory model to its on-disk output directory.
            setattr(getattr(self, lattice), "uuid", prefix)

        def get_lattice_prefix(self, lattice: str) -> str:
            # Retrieve the UUID prefix currently assigned to a lattice section.
            return getattr(self, lattice).uuid

        def get_lattice_screens(self, lattice: str) -> List[Screen]:
            # Return all Screen elements in a specific lattice section.
            return getattr(self, lattice).screens

        def set_screen_update_flag(self, screen: str, updated: bool):
            # Mark a single screen element as updated/not-updated.
            # Used to track which screens have fresh image data available from
            # the simulation so the API knows what to push to clients.
            screenElement = self.get_element(screen)
            setattr(screenElement, "updated", updated)

        def set_lattice_update_flag(self, lattice: str, updated: bool):
            # Mark every element in a lattice section that has an `updated` attribute.
            # Also propagates the flag down to the Camera sub-object on Screen elements,
            # since a Screen has both screen-level and camera-level update state.
            for elem in getattr(self, lattice).get_elements():
                if hasattr(elem, "updated"):
                    setattr(elem, "updated", updated)
                    if isinstance(elem, Screen):
                        setattr(elem.camera, "updated", updated)

        def set_screen_array(self, lattice: str, screen_name: str, arraydata):
            # Store raw image array data on a lattice section.
            # Note: this sets arraydata on the Section, not on the individual screen —
            # so only one screen's data can be stored at a time per section.
            setattr(getattr(self, lattice), "arraydata", arraydata)

        def get_screens(self) -> list:
            # Collect the names of all Screen elements across every lattice section.
            # Silently skips sections with no screens attribute.
            screens = []
            for lattice in lattice_names:
                try:
                    for screen in getattr(self, lattice).screens:
                        screens.append(screen.name)
                except Exception:
                    pass
            return screens

        def get_bpms(self) -> list:
            # Collect the names of all BPM elements across every lattice section.
            # Silently skips sections with no bpms attribute.
            bpms = []
            for lattice in lattice_names:
                try:
                    for bpm in getattr(self, lattice).bpms:
                        bpms.append(bpm.name)
                except Exception:
                    pass
            return bpms

        def get_elements_by_type(self, elem: str) -> list:
            # Return the names of all elements of a given type (e.g. "magnets",
            # "cavities") across every lattice section.
            # `elem` must match an attribute name on the Section schema.
            elems = []
            for lattice in lattice_names:
                try:
                    lat = getattr(self, lattice)
                    elems += [e.name for e in getattr(lat, elem)]
                except Exception:
                    pass
            return elems

        def get_elements_by_type_and_section(self, lattice: str, elem: str) -> list:
            # Return the element objects (not just names) of a given type within a
            # specific lattice section. Returns the full element list, not just names.
            elems = []
            try:
                lat = getattr(self, lattice)
                elems = getattr(lat, elem)
            except Exception:
                pass
            return elems

        def get_element(self, name: str) -> Element | dict:
            # Find and return the first element whose name matches across all sections.
            # Returns the Element class itself (not an instance) if not found —
            # which is arguably a bug; callers should check the return type.
            for lattice in lattice_names:
                for elem in getattr(self, lattice).get_elements():
                    if elem.name == name:
                        return elem
            return Element  # Fallback: returns the class, not an instance.

        def get_elements(self) -> List:
            # Flatten all elements from every lattice section into a single list.
            elems = []
            for lattice in lattice_names:
                elems += getattr(self, lattice).get_elements()
            return elems

        def get_elements_dict(self) -> Dict:
            # Build a {element_name: element_object} dict across all sections.
            # If two sections have an element with the same name, the later one wins.
            elems = {}
            for lattice in lattice_names:
                for elem in getattr(self, lattice).get_elements():
                    elems.update({elem.name: elem})
            return elems

        def get_elements_by_section(self, uuid: str) -> Lattice:
            # Serialise the full multi-section accelerator model into a Lattice schema
            # object suitable for API responses or saving to disk.
            # `uuid` is stamped onto the resulting Lattice so consumers know which
            # simulation run produced this snapshot.
            sections = {}
            generator = None
            for lattice in lattice_names:
                if lattice == "generator":
                    # The Generator section is stored separately in the Lattice schema,
                    # not as one of the named beamline sections.
                    generator = getattr(self, lattice)
                else:
                    lat = getattr(self, lattice)
                    # Seed the section dict with the metadata fields every Section has.
                    sections.update(
                        {
                            lattice: {
                                "uuid": self.get_lattice_prefix(lattice),  # Run prefix for this section.
                                "model": lat.model,                        # Optics model file reference.
                                "initial_conditions": lat.initial_conditions  # Beam params at section entry.,
                            }
                        }
                    )
                    # Append each element-type list (screens, BPMs, etc.) into the
                    # section dict. An empty list is written even if the section has
                    # no elements of that type, keeping the schema consistent.
                    for typ in [
                        "screens",
                        "bpms",
                        "cavities",
                        "magnets",
                        "lasers",
                        "markers",
                    ]:
                        sections[lattice].update({typ: []})
                        if getattr(lat, typ):
                            for elem in getattr(lat, typ):
                                sections[lattice][typ].append(elem)

            # Construct and return the top-level Lattice schema object, converting
            # each section dict back into a Section schema instance.
            return Lattice(
                uuid=uuid,
                sections={k: Section(name=k, **v) for k, v in sections.items()},
                generator=generator,
            )
