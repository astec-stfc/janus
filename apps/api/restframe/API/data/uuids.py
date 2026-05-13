import os
from uuid import UUID, uuid4


def is_valid_uuid(uuid_to_test: uuid4, version: float = 4) -> uuid4:
    """
    Check if uuid_to_test is a valid UUID.

     Parameters
    ----------
    uuid_to_test : str
    version : {1, 2, 3, 4}

     Returns
    -------
    `True` if uuid_to_test is a valid UUID, otherwise `False`.

     Examples
    --------
    >>> is_valid_uuid('c9bf9e57-1685-4c89-bafb-ff5af830be8a')
    True
    >>> is_valid_uuid('c9bf9e58')
    False
    """

    try:
        uuid_obj = UUID(uuid_to_test, version=version)
    except ValueError:
        return False
    return str(uuid_obj) == uuid_to_test


def create_uuid(rundir: str = "./CLARA/") -> str:
    """Return a random uuid."""
    uuid = uuid4()
    existing_uuids = get_existing_uuids(rundir)
    while uuid in existing_uuids:
        uuid = uuid4()
    return str(uuid)


def get_existing_uuids(rundir: str = "./CLARA/") -> list:
    """Return a list of subdirs that are valid uuid's"""
    return [
        name
        for name in os.listdir(rundir)
        if is_valid_uuid(os.path.basename(name))
        and os.path.isdir(rundir + name)
        and os.path.isfile(rundir + name + "/Beam_Summary.hdf5")
    ]
