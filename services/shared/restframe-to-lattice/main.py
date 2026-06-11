from janus_common.utils.kafka_restframe import API
from janus_common.utils.comms_handler import get_lattice_uuids, add_lattice


class Sender(API):
    def __init__(self):
        super().__init__(group_id="restframe-to-lattice")

    def on_msg(self, event, message):
        pass


if __name__ == "__main__":
    sender = Sender()
    sender.forever_loop()
