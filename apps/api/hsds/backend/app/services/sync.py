#!/usr/bin/env python3

from pathlib import Path, PurePosixPath
import h5py
import h5pyd
from h5pyd._apps.utillib import load_file as h5pyd_load_file
import requests
import subprocess
import os
import logging
import sys
import time
import threading
import itertools
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from app.services.notify import publish, FOLDER_UPLOADED_TOPIC

_created_folders = set()
_folder_lock = threading.Lock()
_importing_domains = set()
_importing_lock = threading.Lock()
# one lock per domain, so the startup scan and a tracking_finished upload of
# the same file wait for each other instead of racing on the same domain
_domain_locks: dict[str, threading.Lock] = {}

ROOT = Path("/data/filestore")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    force=True,
)

HDF_EXTENSIONS = {".hdf5", ".openpmd.hdf5"}
# Only outputs something reads from HSDS are uploaded (lattice-to-epics reads
# SCR/MARK/APER/START beam arrays); BPM, laser etc. are skipped. Matched
# against the dash-separated parts of the name, e.g. JFEL-S05-DIA-SCR-01.
SUPPORTED_OUTPUTS = {"SCR", "MARK", "APER", "START"}
# whole filenames that are always uploaded; they have no dash-separated type
# (Twiss_Summary feeds the beam-summary PVs)
ALWAYS_UPLOADED = {"Twiss_Summary.hdf5"}

# HSDS (config.yml `max_task_count`) rejects requests with 503 once too many
# tasks are in flight, so uploads must be throttled rather than run with high
# parallelism. With the default HSDS config, 8 concurrent uploads already
# produce 503s and aren't faster than 4.
IMPORT_WORKERS = int(os.getenv("HSDS_IMPORT_WORKERS", "4"))
LOAD_MAX_RETRIES = int(os.getenv("HSDS_LOAD_MAX_RETRIES", "5"))
LOAD_RETRY_BACKOFF = float(os.getenv("HSDS_LOAD_RETRY_BACKOFF", "2"))
# per-request retries inside h5pyd, as hsload's --retries (default 3)
HSDS_RETRIES = int(os.getenv("HSDS_REQUEST_RETRIES", "3"))

# Linking (metadata only, data read from the source file) is off by default:
# with h5pyd 1.0.0 / h5json 2.0.0 it rejects every contiguous dataset ("Only
# datasets with 'H5D_CHUNKED' layout can be resizable", even when maxshape ==
# shape), so each file paid for a failed attempt before the full copy. The
# files are small enough that a full copy costs about the same.
LINK_ENABLED = os.getenv("HSDS_LINK", "false").lower() in ("1", "true", "yes")

# Where the filestore is mounted inside the hsds container, as a
# "<bucket>/<prefix>" path relative to HSDS's root_dir (/hsds-store).
LINK_ROOT = os.getenv("HSDS_LINK_ROOT", "hsdstest/_filestore").strip("/")

# Shared by the startup scan and tracking_finished uploads, so together they
# never exceed IMPORT_WORKERS concurrent uploads.
_pool = ThreadPoolExecutor(max_workers=IMPORT_WORKERS)

# Each upload only ever talks to a single SN endpoint, so with
# multiple SN replicas running we must round-robin across them ourselves or
# the extras sit idle. Rather than hardcoding a port per replica (which
# would need updating every time target_sn_count changes), discover the
# live SN list from HSDS's own /about endpoint.
HS_ENDPOINT = os.getenv("HS_ENDPOINT", "http://hsds:5101")

_sn_endpoint_cycle = None
_sn_endpoint_lock = threading.Lock()


def discover_sn_endpoints() -> list[str]:
    # explicit override, mainly for tests/non-standard deployments
    override = os.getenv("HS_ENDPOINTS")
    if override:
        return [e.strip() for e in override.split(",") if e.strip()]

    try:
        response = requests.get(f"{HS_ENDPOINT}/about", timeout=5)
        response.raise_for_status()
        urls = response.json().get("sn_urls")
        if urls:
            return urls
    except Exception:
        logging.warning("Could not discover SN endpoints from %s/about", HS_ENDPOINT)

    return [HS_ENDPOINT]


def next_sn_endpoint() -> str:
    global _sn_endpoint_cycle
    with _sn_endpoint_lock:
        if _sn_endpoint_cycle is None:
            endpoints = discover_sn_endpoints()
            logging.info("Using SN endpoints: %s", endpoints)
            _sn_endpoint_cycle = itertools.cycle(endpoints)
        return next(_sn_endpoint_cycle)


def build_domain(file_path: Path) -> str:
    relative = file_path.relative_to(ROOT)
    name = relative.name
    for ext in (
        ".openpmd.hdf5",
        ".hdf5",
    ):
        if name.endswith(ext):
            name = name.removesuffix(ext)
            break
    return "/" + str(relative.with_name(name))


def domain_exists(domain: str) -> bool:

    try:
        # must close, otherwise each check leaks an open HSDS session
        with h5pyd.File(domain, "r"):
            return True

    except Exception:
        return False


def domain_state(domain: str, file_path: Path) -> str:
    """Return "missing", "stale" or "current" for `domain` versus `file_path`.

    A rerun rewrites the files in its uuid folder, so an existing domain alone
    doesn't mean it holds the current data: it's only current if it was
    created after the file last changed.
    """
    try:
        # must close, otherwise each check leaks an open HSDS session
        with h5pyd.File(domain, "r") as f:
            created = f.created
    except Exception:
        return "missing"

    if isinstance(created, datetime):
        created = created.timestamp()
    if created is None:
        logging.warning("HSDS reported no creation time for %s, treating it as current", domain)
        return "current"

    return "current" if float(created) >= file_path.stat().st_mtime else "stale"


def build_link_path(file_path: Path) -> str:
    # With --link, HSDS itself reads the dataset chunks from the source file,
    # so the link must be a "<bucket>/<key>" path HSDS resolves under its own
    # root_dir, not our /data/filestore path (hsload rejects absolute paths).
    return f"{LINK_ROOT}/{file_path.relative_to(ROOT).as_posix()}"


def load_file(file_path: Path, domain: str) -> bool:

    # hsmv's rename relies on HSDS's linked_domain create, which this HSDS
    # server/h5pyd combination doesn't honor (it silently creates a fresh
    # empty root instead of linking to the uploaded one), so the load goes
    # straight to the final domain. Readers may briefly see a partially
    # populated domain while a (re)load is in progress.
    endpoint = next_sn_endpoint()

    logging.info("Importing %s -> %s (endpoint=%s)", file_path, domain, endpoint)

    # HSDS returns 503 when its task queue is saturated; retry with backoff
    # rather than dropping the import. Each attempt opens the domain with
    # mode "w", which overwrites whatever a stale upload or a failed attempt
    # left behind.
    link = LINK_ENABLED
    for attempt in range(1, LOAD_MAX_RETRIES + 1):
        error = _load_in_process(file_path, domain, endpoint, link)

        # linked datasets must be fixed-size (and this h5pyd rejects linked
        # contiguous datasets too), so fall back to a full copy
        if link and error and "can be resizable" in error:
            logging.warning("%s can't be linked (%s), falling back to a full upload", file_path, error)
            link = False
            error = _load_in_process(file_path, domain, endpoint, link)

        if error is None:
            return True

        reason = error
        if attempt < LOAD_MAX_RETRIES:
            sleep_time = LOAD_RETRY_BACKOFF * attempt
            logging.warning(
                "Load failed for %s -> %s (attempt %d/%d): %s, retrying in %.1fs",
                file_path,
                domain,
                attempt,
                LOAD_MAX_RETRIES,
                reason,
                sleep_time,
            )
            time.sleep(sleep_time)

    logging.error(
        "Load failed for %s -> %s after %d attempts: %s",
        file_path,
        domain,
        LOAD_MAX_RETRIES,
        reason,
    )
    # don't leave a partial domain behind: domain_state() would treat it as
    # uploaded, so later scans would never retry it and its folder would be
    # reported complete
    _remove_domain(domain)
    return False


def _remove_domain(domain: str):
    # only used after the final failed attempt, so the extra process is fine
    subprocess.run(
        ["hsrm", "-r", domain],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _load_in_process(file_path: Path, domain: str, endpoint: str, link: bool) -> str | None:
    """Do what `hsload` does, without starting a new Python process.

    Each hsload run spent ~0.8s just starting Python and importing
    h5py/h5pyd/numpy, far longer than uploading one of these small files.
    Returns None on success, or the error message.
    """
    try:
        with h5py.File(file_path, "r") as fin, h5pyd.File(
            domain, mode="w", endpoint=endpoint, retries=HSDS_RETRIES
        ) as fout:
            h5pyd_load_file(
                fin,
                fout,
                dataload="link" if link else "ingest",
                s3path=build_link_path(file_path) if link else None,
            )
        return None
    except SystemExit as e:
        # utillib reports some problems with sys.exit() rather than raising
        return f"h5pyd load_file exited with status {e.code}"
    except Exception as e:
        logging.debug("Load of %s -> %s failed", file_path, domain, exc_info=True)
        return f"{type(e).__name__}: {e}"


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


def is_supported_output(name: str) -> bool:
    if name in ALWAYS_UPLOADED:
        return True
    # match whole parts so a name that merely contains the letters isn't
    # picked up
    return not SUPPORTED_OUTPUTS.isdisjoint(name.split(".")[0].split("-"))


def find_hdf_files(folder: Path = ROOT):
    # one pass with endswith: globbing per extension would return every
    # .openpmd.hdf5 file twice, since it also matches *.hdf5
    for path in folder.rglob("*"):
        if (
            path.is_file()
            and path.name.endswith(tuple(HDF_EXTENSIONS))
            and is_supported_output(path.name)
        ):
            yield path


def import_file(file_path: Path) -> bool:
    """Upload `file_path` unless HSDS already has it. Returns True on success."""
    try:
        domain = build_domain(file_path)
    except Exception:
        logging.exception("Failed to build domain for %s", file_path)
        return False

    with _importing_lock:
        domain_lock = _domain_locks.setdefault(domain, threading.Lock())

    with domain_lock:
        with _importing_lock:
            _importing_domains.add(domain)
        try:
            state = domain_state(domain, file_path)
            if state == "current":
                logging.info("Skipping up-to-date domain %s", domain)
                return True

            ensure_parent_exists(domain)

            return load_file(file_path, domain)
        except Exception:
            # unexpected errors must not be silently dropped by the pool, since
            # the startup scan never consumes its results
            logging.exception("Unexpected error importing %s -> %s", file_path, domain)
            return False
        finally:
            with _importing_lock:
                _importing_domains.discard(domain)


def full_scan():
    files = list(find_hdf_files())
    list(_pool.map(import_file, files))


def upload_folder(folder: Path, context: dict | None = None) -> bool:
    """Upload every HDF file in `folder`, then announce it on Kafka.

    `context` (e.g. the triggering run's client_id/request_id/uuid) is copied
    into the message so readers can match it to their run. Returns False if
    any file failed, so the caller can decide whether to retry; nothing is
    published in that case.
    """
    files = list(find_hdf_files(folder))
    if not files:
        # still announced below, so readers waiting on this run aren't stuck
        logging.warning("No HDF files found in %s", folder)

    results = list(_pool.map(import_file, files))
    failed = [f for f, ok in zip(files, results) if not ok]
    if failed:
        logging.error(
            "%d of %d file(s) in %s failed to upload: %s",
            len(failed),
            len(files),
            folder,
            ", ".join(f.name for f in failed),
        )
        return False

    relative = folder.relative_to(ROOT)
    message = {
        **(context or {}),
        "folder": str(relative),
        "domain_folder": "/" + str(relative),
        "domains": [build_domain(f) for f in files],
        "file_count": len(files),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if publish(FOLDER_UPLOADED_TOPIC, message):
        logging.info("Published %s for %s", FOLDER_UPLOADED_TOPIC, relative)
    return True


def folder_upload_status(folder: Path) -> dict:
    """Report upload completeness for all HDF files under `folder`."""
    files = list(find_hdf_files(folder))

    with _importing_lock:
        in_flight = set(_importing_domains)

    pending = []
    domains = []
    for file_path in files:
        domain = build_domain(file_path)
        domains.append(domain)
        # uploads write straight to the final domain, so it exists while a
        # load is still in progress
        if domain in in_flight or not domain_exists(domain):
            pending.append(str(file_path.relative_to(ROOT)))

    return {
        "total": len(files),
        "uploaded": len(files) - len(pending),
        "pending": pending,
        "domains": domains,
        "complete": not pending,
    }


def main():
    full_scan()


if __name__ == "__main__":
    sys.exit(main())
