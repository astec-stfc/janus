import json
import logging
import os
import threading

from kafka import KafkaProducer

BROKER_HOST = os.getenv("BROKER_HOST", "broker")
KAFKA_PORT = int(os.getenv("KAFKA_PORT", "9092"))
FOLDER_UPLOADED_TOPIC = os.getenv("HSDS_FOLDER_UPLOADED_TOPIC", "hdf_folder_uploaded")
SEND_TIMEOUT = float(os.getenv("KAFKA_SEND_TIMEOUT", "10"))

_producer = None
_producer_lock = threading.Lock()


def _get_producer():
    # created lazily and retried on each publish, so a broker that is down
    # (or absent, e.g. the standalone hsds compose stack) doesn't stop the
    # uploader from starting
    global _producer
    with _producer_lock:
        if _producer is None:
            _producer = KafkaProducer(
                bootstrap_servers=f"{BROKER_HOST}:{KAFKA_PORT}",
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
        return _producer


def publish(topic: str, message: dict) -> bool:
    try:
        # block on the result so failures are logged rather than lost
        _get_producer().send(topic, value=message).get(timeout=SEND_TIMEOUT)
        return True
    except Exception:
        logging.exception("Failed to publish to Kafka topic %s", topic)
        return False
