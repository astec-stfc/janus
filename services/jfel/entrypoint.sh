#!/bin/bash
echo "Waiting for Comms...";
until $(curl -X GET --output /dev/null --silent --head --fail http://${LATTICE_API_HOST:-lattice_api}:${LATTICE_API_PORT:-5000}/v1/lattice/runs/); do sleep 0.1; done
echo "Comms started...";
echo "Waiting for endpoint population...";
while true; do
    RESPONSE=$(curl -s -f http://${LATTICE_API_HOST:-lattice_api}:${LATTICE_API_PORT:-5000}/v1/lattice/runs/)

    echo "curl -X GET 'http://${LATTICE_API_HOST:-lattice_api}:${LATTICE_API_PORT:-5000}/v1/lattice/runs/'"
    echo "Response: $RESPONSE"

    if [ "$RESPONSE" = "[]" ]; then
        sleep 1
    else
        break
    fi
done
echo "endpoint available...";
until </dev/tcp/${BROKER_HOST:-broker}/${KAFKA_PORT:-9092}; do
  sleep 0.1
done

echo "Kafka broker is ready..."
python3 main.py
