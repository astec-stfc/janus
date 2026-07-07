"""Track with RestFrame and forward completed results to lattice-api.

This service used to fetch a completed lattice as binary, decode it back into a
schema object, and then POST a large JSON body to lattice-api. The current flow
keeps the result in binary form for the RestFrame -> lattice-api hop so only the
storage service performs the decode.
"""

from time import perf_counter
import time
from janus_common.utils.kafka_restframe import API
from janus_common.utils.comms_handler import add_lattice_binary, get_lattice_request
from janus_common.utils.flow_log import flow_log


class Sender(API):
    def __init__(self, name="get-magnets-and-track"):
        super().__init__(group_id="lattice-to-restframe")
        self.name = name
        self.lattice = None

    def run_restframe(
        self, wait: bool = True, client_id: str = None, request_id: str = None
    ):
        # self.modify_object("generator", "number_of_particles", int(2 ** (3 * 4)))
        if wait:
            self.track_and_wait(client_id=client_id, request_id=request_id)
        else:
            self.track(client_id=client_id, request_id=request_id)

    def tracking_complete(self) -> bool:
        return self.finished_tracking

    def on_msg(self, event, message):
        client_id = event.get("client_id")
        request_id = event.get("request_id")
        if not request_id:
            raise ValueError("lattice_ready message is missing required request_id")

        wait_s = (int(time.time() * 1000) - message.timestamp) / 1000
        queue_info = (
            f", queued for {wait_s:.1f}s before consuming" if wait_s > 0.1 else ""
        )
        flow_log(
            "G03 restframe.submit",
            "S2/6",
            client_id=client_id,
            request_id=request_id,
            current=f"consumed message from topic 'lattice_ready'{queue_info}, fetching lattice request and POSTing to track to restframe",
            next_step="restframe to publish to topic 'tracking_started' and begin simulation",
        )

        self.lattice = get_lattice_request(request_id=request_id)
        if self.lattice is None:
            raise RuntimeError(
                f"No pending lattice request found for request_id: {request_id}"
            )

        t0 = perf_counter()
        self.modify_lattice(self.lattice)
        t1 = perf_counter()

        self.run_restframe(wait=False, client_id=client_id, request_id=request_id)
        while not self.tracking_complete():
            # Avoid hammering /track in a busy loop; high-frequency polling can
            # contend with result serialization work right after tracking.
            time.sleep(0.05)

        t2 = perf_counter()
        # Keep the post-tracking handoff in binary form to avoid a decode ->
        # model_dump -> large JSON POST loop between services.
        result_lattice_binary = self.get_lattice_binary(compress=True)
        t3 = perf_counter()

        store_result = add_lattice_binary(
            binary_payload=result_lattice_binary,
            client_id=client_id,
            request_id=request_id,
        )
        t4 = perf_counter()

        print(
            "lattice-to-restframe timings ",
            f"uuid={store_result.get('uuid')} ",
            f"modify_lattice={t1-t0:.3f}s ",
            f"wait_for_tracking={t2-t1:.3f}s ",
            f"get_lattice_binary={t3-t2:.3f}s ",
            f"add_lattice_post={t4-t3:.3f}s ",
        )

        self.producer.send(
            "new_results",
            value={
                "request_id": request_id,
                "uuid": store_result.get("uuid"),
                "client_id": client_id,
            },
        )


if __name__ == "__main__":
    time.sleep(10)
    sender = Sender()
    sender.subscribe(["lattice_ready"])
    print("starting forever loop")
    sender.forever_loop()
