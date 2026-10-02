import json
import logging
import os
import threading
import time

from kafka import KafkaConsumer

from app.services.notify import BROKER_HOST, KAFKA_PORT
from app.services.sync import ROOT, full_scan, upload_folder

TRACKING_FINISHED_TOPIC = os.getenv("TRACKING_FINISHED_TOPIC", "tracking_finished")
CONSUMER_GROUP = os.getenv("HSDS_CONSUMER_GROUP", "hsds_backend")
# Uploading a run can take minutes; Kafka evicts a consumer that goes longer
# than this between polls, so it must cover the slowest folder upload.
MAX_POLL_INTERVAL_MS = int(os.getenv("HSDS_MAX_POLL_INTERVAL_MS", str(60 * 60 * 1000)))
CONNECT_RETRY_SECONDS = float(os.getenv("KAFKA_CONNECT_RETRY_SECONDS", "10"))
# Folders with files that exhausted their hsload retries (e.g. HSDS was down)
# are retried on this interval until they upload and get announced.
FOLDER_RETRY_SECONDS = float(os.getenv("HSDS_FOLDER_RETRY_SECONDS", "600"))

# folder -> context of the run that triggered it, re-sent on a successful retry
_failed_folders: dict = {}
_failed_lock = threading.Lock()


def _connect() -> KafkaConsumer:
    while True:
        try:
            return KafkaConsumer(
                TRACKING_FINISHED_TOPIC,
                bootstrap_servers=f"{BROKER_HOST}:{KAFKA_PORT}",
                group_id=CONSUMER_GROUP,
                # a brand new group starts from now rather than replaying every
                # historical run; the startup scan covers anything older.
                # After that, committed offsets pick up runs that finished
                # while this service was down.
                auto_offset_reset="latest",
                enable_auto_commit=False,
                max_poll_records=1,
                max_poll_interval_ms=MAX_POLL_INTERVAL_MS,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            )
        except Exception:
            logging.warning(
                "Kafka broker %s:%s unavailable, retrying in %.0fs",
                BROKER_HOST,
                KAFKA_PORT,
                CONNECT_RETRY_SECONDS,
            )
            time.sleep(CONNECT_RETRY_SECONDS)


def handle_tracking_finished(message: dict):
    uuid = message.get("uuid") if isinstance(message, dict) else None
    if not uuid:
        logging.warning("Ignoring %s message without a uuid: %s", TRACKING_FINISHED_TOPIC, message)
        return

    folder = (ROOT / str(uuid)).resolve()
    if folder.parent != ROOT.resolve():
        logging.warning("Ignoring %s message with invalid uuid %r", TRACKING_FINISHED_TOPIC, uuid)
        return
    if not folder.is_dir():
        logging.warning("Run folder %s does not exist", folder)
        return

    logging.info("Tracking finished for %s, uploading %s", uuid, folder)
    # readers (e.g. lattice-to-epics) filter by client_id and match their run
    # by request_id/uuid, so pass them through to hdf_folder_uploaded
    context = {
        "uuid": str(uuid),
        "client_id": message.get("client_id"),
        "request_id": message.get("request_id"),
    }
    _upload_or_queue_retry(folder, context)


def _upload_or_queue_retry(folder, context):
    ok = upload_folder(folder, context)
    with _failed_lock:
        if ok:
            _failed_folders.pop(folder, None)
        else:
            _failed_folders[folder] = context


def _retry_failed_folders():
    while True:
        time.sleep(FOLDER_RETRY_SECONDS)
        with _failed_lock:
            failed = list(_failed_folders.items())
        for folder, context in failed:
            if not folder.is_dir():
                # run deleted since it failed
                with _failed_lock:
                    _failed_folders.pop(folder, None)
                continue
            logging.info("Retrying upload of %s", folder)
            _upload_or_queue_retry(folder, context)


def consume_forever():
    consumer = _connect()
    logging.info("Listening for %s on %s:%s", TRACKING_FINISHED_TOPIC, BROKER_HOST, KAFKA_PORT)
    for record in consumer:
        try:
            handle_tracking_finished(record.value)
        except Exception:
            logging.exception("Failed to handle %s message %s", TRACKING_FINISHED_TOPIC, record.value)
        # commit even on failure: failed folders are retried by
        # _retry_failed_folders, and redelivering could block newer runs
        consumer.commit()


def start_sync():
    if not ROOT.exists():
        logging.info("Filestore %s does not exist, creating it", ROOT)
        ROOT.mkdir(parents=True, exist_ok=True)

    # listen straight away so new runs aren't stuck behind the startup scan;
    # the shared upload pool and per-domain locks keep the two from clashing
    threading.Thread(target=consume_forever, daemon=True).start()
    threading.Thread(target=_retry_failed_folders, daemon=True).start()

    logging.info("Starting startup scan of %s", ROOT)
    full_scan()
    logging.info("Startup scan completed")
