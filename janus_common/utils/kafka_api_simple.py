from typing import Union
from janus_common.schemas.elements import Lattice
from kafka import KafkaProducer, KafkaConsumer
import json
import time


class KafkaAPI(KafkaConsumer):
    # MIGHT NEED TO CHANGE URL HERE, IF CONTAINER IS ON HOST THIS IS OKAY,
    # OTHERWISE MIGHT NEED DOCKER-NAME.
    def __init__(
        self,
        host: str,
        port: int,
        group_id='group_api',
        frequency = 5,
    ):
        super().__init__(
            bootstrap_servers=f"{host}:{port}",
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')) 
        )

        self.producer = KafkaProducer(
            bootstrap_servers=f"{host}:{port}",
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            
        )
        
        self.frequency = frequency

        
    def msg_behaviour(self, topic) -> None:
        raise NotImplemented("Just implement this please for the loop to work")
    
    def loop_to_send_forever(self,topic):
        while True:
            time.sleep(self.frequency)
            self.msg_behaviour(topic)

    def transform_data_output(self, uuid:int):
        return {"uuid":uuid }
    
    def on_msg(self, uuid:int,message) -> None:
        raise NotImplemented("Just implement this please for the loop to work")
    
    def forever_loop(self):
        for message in self:
            data = message.value
            self.on_msg(data,message)
            self.master_received = True
    
    def json_to_uuid(self, uuid_json) -> Lattice:
        return uuid_json["uuid"]

    # def modify_lattice(self, lattice: Lattice):
    #     self.producer.send("lattice", value=self.transform_data_output(lattice))

    def modify_object(
        self, name: str, parameter: str, value: Union[str, float, int, bool]
    ):
        self.producer.send("info_json", value={"name": name, "parameter": parameter, "value": value})
    
    def send_over_uuid(self,topic,uuid):
        print(f"SENDING UUID {uuid} OVER TOPIC {topic}")
        self.producer.send(topic, value=self.transform_data_output(uuid))
        # return {"topic":topic,"lattice":lattice}

