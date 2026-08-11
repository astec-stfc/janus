#!/usr/bin/env python3

from pathlib import Path, PurePosixPath
import h5pyd
import subprocess
import os
import logging
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

_created_folders = set()
_folder_lock = threading.Lock()

ROOT = Path("/data/filestore")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    force=True,
)

HDF_EXTENSIONS = {".h5", ".hdf5", ".openpmd.hdf5"}


def build_domain(file_path: Path) -> str:
    relative = file_path.relative_to(ROOT)
    name = relative.name
    for ext in (
        ".openpmd.hdf5",
        ".hdf5",
        ".h5",
    ):
        if name.endswith(ext):
            name = name.removesuffix(ext)
            break
    return "/" + str(relative.with_name(name))


def domain_exists(domain: str) -> bool:

    try:
        h5pyd.File(domain, "r")
        return True

    except Exception:
        return False


def load_file(file_path: Path, domain: str) -> bool:

    logging.info("Importing %s -> %s", file_path, domain)

    result = subprocess.run(
        [
            "hsload",
            str(file_path),
            domain,
        ]
    )

    return result.returncode == 0


def ensure_parent_exists(domain: str):

    parent = str(PurePosixPath(domain).parent)

    if parent == "/":
        return

    with _folder_lock:

        if parent in _created_folders:
            return

        subprocess.run(
            ["hstouch", parent + "/"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        _created_folders.add(parent)


def find_hdf_files():
    for ext in HDF_EXTENSIONS:
        yield from ROOT.rglob(f"*{ext}")


def import_file(file_path):
    domain = build_domain(file_path)
    logging.info(f"Importing {file_path} -> {domain}")
    if domain_exists(domain):
        logging.info("Skipping existing domain %s", domain)
        return

    ensure_parent_exists(domain)

    load_file(file_path, domain)


def full_scan():
    files = list(find_hdf_files())
    with ThreadPoolExecutor(max_workers=8) as pool:
        pool.map(import_file, files)


def main():
    full_scan()


if __name__ == "__main__":
    sys.exit(main())
