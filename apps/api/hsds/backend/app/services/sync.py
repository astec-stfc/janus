#!/usr/bin/env python3

from pathlib import Path, PurePosixPath
import h5pyd
import subprocess
import os
import logging
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor

_created_folders = set()
_folder_lock = threading.Lock()
_importing_domains = set()
_importing_lock = threading.Lock()

ROOT = Path("/data/filestore")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    force=True,
)

HDF_EXTENSIONS = {".h5", ".hdf5", ".openpmd.hdf5"}

# HSDS (config.yml `max_task_count`) rejects requests with 503 once too many
# tasks are in flight, so hsload uploads must be throttled rather than run
# with high parallelism.
IMPORT_WORKERS = int(os.getenv("HSDS_IMPORT_WORKERS", "2"))
LOAD_MAX_RETRIES = int(os.getenv("HSDS_LOAD_MAX_RETRIES", "5"))
LOAD_RETRY_BACKOFF = float(os.getenv("HSDS_LOAD_RETRY_BACKOFF", "2"))


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

    # HSDS returns 503 when its task queue is saturated; retry with backoff
    # rather than dropping the import.
    for attempt in range(1, LOAD_MAX_RETRIES + 1):
        result = subprocess.run(
            [
                "hsload",
                str(file_path),
                domain,
            ]
        )
        if result.returncode == 0:
            return True

        if attempt < LOAD_MAX_RETRIES:
            sleep_time = LOAD_RETRY_BACKOFF * attempt
            logging.warning(
                "hsload failed for %s -> %s (attempt %d/%d), retrying in %.1fs",
                file_path, domain, attempt, LOAD_MAX_RETRIES, sleep_time,
            )
            time.sleep(sleep_time)

    logging.error("hsload failed for %s -> %s after %d attempts", file_path, domain, LOAD_MAX_RETRIES)
    return False


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

    with _importing_lock:
        if domain in _importing_domains:
            logging.info("Import already in progress for domain %s, skipping", domain)
            return
        _importing_domains.add(domain)

    try:
        logging.info(f"Importing {file_path} -> {domain}")
        if domain_exists(domain):
            logging.info("Skipping existing domain %s", domain)
            return

        ensure_parent_exists(domain)

        load_file(file_path, domain)
    finally:
        with _importing_lock:
            _importing_domains.discard(domain)


def full_scan():
    files = list(find_hdf_files())
    with ThreadPoolExecutor(max_workers=IMPORT_WORKERS) as pool:
        pool.map(import_file, files)


def main():
    full_scan()


if __name__ == "__main__":
    sys.exit(main())
