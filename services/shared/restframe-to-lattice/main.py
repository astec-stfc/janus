from common.kafka_restframe import API
from common.comms_handler import get_lattice_uuids, add_lattice


class Sender(API):
    def __init__(self):
        super().__init__(group_id="restframe-to-lattice")
        self.current_lattice = self.get_lattice()

    def latest_uuid(self) -> bool:
        return self.get_latest_run_uuid()

    def on_msg(self, uuid, message):
        sim_uuid = uuid["uuid"]
        previous_uuids = get_lattice_uuids()
        if sim_uuid not in previous_uuids:
            self.current_lattice = self.get_lattice()
            add_lattice(
                lattice=self.current_lattice,
            )
            print("LATTICE ADDED")


if __name__ == "__main__":
    sender = Sender()
    sender.subscribe(["tracking_finished"])
    sender.forever_loop()
