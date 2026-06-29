import time
from janus_common.utils.kafka_restframe import API
from janus_common.utils.comms_handler import add_lattice, get_lattice_request
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

        self.modify_lattice(self.lattice)
        self.run_restframe(wait=False, client_id=client_id, request_id=request_id)
        while not self.tracking_complete():
            continue

        # Safe window: restframe still holds this client's completed results.
        # Grab them now before the next lattice_ready message overwrites restframe.
        # add_lattice() blocks until the DB write is confirmed, so lattice-to-epics
        # cannot consume before the uuid is in the DB.
        flow_log(
            "G07 results.store",
            "S5/6",
            client_id=client_id,
            request_id=request_id,
            current="RestFrame completed tracking; fetching completed results and POSTing them to the lattice API",
            next_step="lattice API to store simulation results and publish topic 'lattice_added'",
        )
        result_lattice = self.get_lattice()
        result_lattice.client_id = client_id
        add_lattice(lattice=result_lattice, request_id=request_id)
        self.producer.send(
            "new_results",
            value={
                "request_id": request_id,
                "uuid": result_lattice.uuid,
                "client_id": client_id,
            },
        )


if __name__ == "__main__":
    time.sleep(10)
    sender = Sender()
    sender.subscribe(["lattice_ready"])
    print("starting forever loop")
    sender.forever_loop()
