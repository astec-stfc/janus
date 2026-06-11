import os

HOST_LOCAL = "localhost"
HOST_LATTICE_API = os.getenv("LATTICE_API_HOST", "lattice_api")
HOST_WEB_RESTFRAME = os.getenv("RESTFRAME_HOST", "restframe")

PORT_COMMS = int(os.getenv("LATTICE_API_PORT", "5000"))
PORT_RESTFRAME = int(os.getenv("RESTFRAME_PORT", "8000"))
BOOTSTRAP_SERVERS = os.getenv("BROKER_HOST", "broker")
KAFKA_PORT = int(os.getenv("KAFKA_PORT", "9092"))

SIGFIG = 5