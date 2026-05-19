from typing import Optional, Dict
import random
import time
from p4p.server.thread import SharedPV
from p4p.server import ServerOperation


def time_in_seconds_and_nanoseconds(timestamp: float = time.time()):
    seconds = int(timestamp // 1)
    nanoseconds = int((timestamp % 1) * 1e9)
    return seconds, nanoseconds


class Handler:

    def __init__(self, *args, **kwargs):
        pass

    def put(self, pv: SharedPV, op: ServerOperation): ...


class BasicHandler(Handler):

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)

    def put(self, pv: SharedPV, op: ServerOperation):
        # Note that timestamps are not automatically
        # handled so we may need to set them ourselves
        if not op.value().raw.changed("timeStamp"):
            timestamp = time.time()
            pv.post(
                op.value(), timestamp=timestamp
            )  # just store and update subscribers
        else:
            pv.post(op.value())
        op.done()


class EnumHandler(Handler):
    def __init__(
        self,
        options: Optional[Dict] = None,
        read_only: bool = False,
    ):
        self.read_only = read_only
        self.read_pv = options["read_pv"]
        self.read_values = options["read_values"]

    def put(self, pv, op):
        if self.read_only:
            op.done(error=f"{op.name()} is read_only")
        if not op.value().changed("timeStamp"):
            seconds, nanoseconds = time_in_seconds_and_nanoseconds(time.time())
            op.value()["timeStamp"] = {
                "secondsPastEpoch": seconds,
                "nanoseconds": nanoseconds,
                "userTag": 0,
            }
        pv.post(op.value())
        delay = random.uniform(1, 2)
        time.sleep(delay)
        if self.read_pv is not None:
            read_value = self.read_values[op.value()["value"]["index"]]
            self.read_pv.post(read_value)
        op.done()
