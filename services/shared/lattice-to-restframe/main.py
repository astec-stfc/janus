from janus_common.utils.kafka_restframe import API
from janus_common.utils.comms_handler import get_lattice


class Sender(API):
    def __init__(self,name="get-magnets-and-track"):
        super().__init__(group_id="lattice-to-restframe") 
        self.name = name
        self.lattice = None

    def run_restframe(self, wait: bool = True):
        self.modify_object(
            "generator", "number_of_particles", int(2 ** (3 * 4))
        )
        if wait:
            self.track_and_wait()
        else:
            self.track()

    def tracking_complete(self) -> bool:
        return self.finished_tracking

    def on_msg(self, uuid, message):
        self.lattice = get_lattice()
        self.modify_lattice(self.lattice)
        self.run_restframe(wait=False)
        while not self.tracking_complete():
            continue


if __name__ == "__main__":
    sender = Sender()
    sender.subscribe(["lattice_ready"])
    print("starting forever loop")
    sender.forever_loop()
