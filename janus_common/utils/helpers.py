import os
import logging
import threading
from time import sleep
from typing import List, Any, Tuple
from itertools import islice
from p4p.client.thread import Context, TimeoutError
from concurrent.futures import ThreadPoolExecutor, as_completed
from p4p.wrapper import Value


def _chunked(iterable, size):
    it = iter(iterable)
    while chunk := list(islice(it, size)):
        yield chunk


def countdown(filename, seconds):
    while seconds > 0:
        print(f"{filename}: {seconds} sec")
        if seconds > 10:
            sleep(5)
            seconds -= 5
        else:
            sleep(1)
            seconds -= 1

def to_camel_case(s):
    parts = s.split("_")
    return parts[0].lower() + "".join(word.capitalize() for word in parts[1:])

class EPICSHelper:
    """Helper class for interacting with EPICS PVs using p4p"""

    def __init__(self, ctx: Context):
        self._ctx = ctx
        self._chunk_size = int(os.environ.get("CHUNKS", 500))
        self._executor = ThreadPoolExecutor(
            max_workers=int(os.environ.get("MAX_WORKERS", 8))
        )

    def epics_scalar(self, v):
        # Structured NTScalar
        if isinstance(v, Value):
            return v["value"]

        # NTScalar wrappers (ntstr, ntint, ntfloat, etc.)
        if hasattr(v, "value"):
            return v.value

        # Already a plain Python type
        return v

    def put_pv(self, pvname: list | str, value: list | Any):
        """Send a value (or list of values) to PVs in EPICS"""
        try:
            self._ctx.put(pvname, value, timeout=5.0, wait=True)
            return True
        except TimeoutError as e:
            print(f"Timeout putting {value} to {pvname}: {e}")
        except Exception as e:
            print(f"Failed to put {value} to {pvname}: {e}")
            return False

    def get_pv(self, pvname: str):
        """Get a value from a PV in EPICS"""
        try:
            return self._ctx.get(pvname, timeout=1.0)
        except TimeoutError as e:
            print(f"Timeout getting value for {pvname}: {e}")
        except Exception as e:
            print(f"Failed to get {pvname}: {e}")
            return None

    def put_pv_list(
        self,
        pvnames: List[str],
        values: List[Any],
        throw: bool = False,
    ) -> List:
        """Send a list of values to a list of PVs in EPICS"""
        try:
            results = self._ctx.put(
                pvnames,
                values,
                timeout=1.0,
                throw=throw,
                wait=True,
            )
            return results
        except TimeoutError as e:
            if throw:
                raise e
            print(f"Timeout putting {values} to {pvnames}: {e}")
            return [e] * len(pvnames)
        except Exception as e:
            if throw:
                raise e
            print(f"Failed to put {values} to {pvnames}: {e}")
            return [e] * len(pvnames)

    def _put_chunk(self, chunk: List[Tuple[str, Any]]) -> None:
        pvs, vals = zip(*chunk)
        normalized_vals = [self._normalize_put_value(v) for v in vals]
        try:
            self._ctx.put(list(pvs), normalized_vals, timeout=0.5, wait=False)
        except Exception as e:
            first_pv = pvs[0] if pvs else None
            first_type = type(normalized_vals[0]).__name__ if normalized_vals else None
            print(
                f"Bulk put error: {e!r} | first_pv={first_pv} | first_type={first_type}"
            )

    def _normalize_put_value(self, value: Any) -> Any:
        """Normalize values for p4p put payloads.

        Converts numpy-like arrays/scalars to native Python types while
        preserving ordinary Python scalar/list values unchanged.
        """
        if isinstance(value, tuple):
            return list(value)

        # ndarray-like objects
        if hasattr(value, "tolist") and not isinstance(
            value, (str, bytes, bytearray, list, dict)
        ):
            try:
                return value.tolist()
            except Exception:
                pass

        # numpy scalar-like objects
        if hasattr(value, "item") and not isinstance(value, (str, bytes, bytearray)):
            try:
                return value.item()
            except Exception:
                pass

        return value

    def set_pv_updates(
        self,
        pv_updates: List[Tuple[str, Any]],
    ) -> None:
        """Bulk-write PVs in chunks, dispatching each chunk as a single p4p put."""
        if not pv_updates:
            return
        filtered = [
            (pv, val) for pv, val in pv_updates if pv is not None and val is not None
        ]
        list(self._executor.map(self._put_chunk, _chunked(filtered, self._chunk_size)))

    @property
    def is_epics_alive(self):
        """Check if EPICS is responding by trying to get a known PV"""
        _pv_to_check = "SIMULATION:STATUS"
        timeout = 1.0
        try:
            self._ctx.get(_pv_to_check, timeout=timeout)
            return True
        except TimeoutError:
            return False
        except Exception:
            return False

    def _log_put_result(
        self,
        results: list,
        set_pvs: list,
        set_vals: list,
    ):
        """Log the result of a put operation to EPICS"""
        for i, result in enumerate(results):
            if result is not None:
                logging.warning(
                    "Failed put to %s: %s value %s",
                    set_pvs[i],
                    type(result),
                    set_vals[i],
                )
            else:
                logging.info("Updated %s", set_pvs[i])


class EPICSStreamer:
    """
    Accumulates PV updates and flushes them in chunks via EPICSHelper.
    Thread-safe: push() can be called from multiple worker threads simultaneously.
    """

    def __init__(self, helper: EPICSHelper):
        self._helper = helper
        self._chunk_size = int(os.environ.get("CHUNKS", 500))
        self._buffer: List[Tuple[str, Any]] = []
        self._lock = threading.Lock()

    def push(self, pv, val) -> None:
        if pv is None or val is None:
            return
        chunk = None
        with self._lock:
            self._buffer.append((pv, val))
            if len(self._buffer) >= self._chunk_size:
                chunk = list(self._buffer)
                self._buffer.clear()
        if chunk:
            self._helper.set_pv_updates(chunk)

    def flush(self) -> None:
        with self._lock:
            chunk = list(self._buffer)
            self._buffer.clear()
        if chunk:
            self._helper.set_pv_updates(chunk)
