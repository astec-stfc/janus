import time

from p4p.nt import NTScalar
from p4p.server import Server, ServerOperation
from p4p.server.thread import SharedPV


def time_in_seconds_and_nanoseconds(timestamp: float):
    seconds = int(timestamp // 1)
    nanoseconds = int((timestamp % 1) * 1e9)
    return seconds, nanoseconds


class Handler:
    def put(self, pv: SharedPV, op: ServerOperation):
        # Note that timestamps are not automatically handled so we may need to set them ourselves
        if not op.value().raw.changed("timeStamp"):
            timestamp = time.time()
            pv.post(
                op.value(), timestamp=timestamp
            )  # just store and update subscribers
        else:
            pv.post(op.value())
        op.done()


def main():
    nt = NTScalar("i", display=True)

    seconds, nanoseconds = time_in_seconds_and_nanoseconds(time.time())

    initial_values = {
        "value": 0,
        "display.description": "PV for seeding ISIS JANUS simulations",
        "timeStamp.secondsPastEpoch": seconds,
        "timeStamp.nanoseconds": nanoseconds,
    }
    pv = SharedPV(nt=nt, initial=initial_values, handler=Handler())
    print("isis ioc started: ISIS:SIM:SEED")
    server = Server.forever(providers=[{"ISIS:SIM:SEED": pv}])


if __name__ == "__main__":
    main()
