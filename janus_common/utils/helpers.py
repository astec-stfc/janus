import logging
from time import sleep
from typing import List, Any, Tuple
from p4p.client.thread import Context, TimeoutError
from concurrent.futures import ThreadPoolExecutor, as_completed
from p4p.wrapper import Value

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

    def set_pv_updates(
        self,
        pv_updates: List[Tuple[str, Any]],
    ) -> None:
        """Set multiple PVs in EPICS using threading for efficiency"""
        if not pv_updates:
            return
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(self.put_pv, pv, val)
                for pv, val in pv_updates
                if pv and val
            ]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print("Error in thread:", e)

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
