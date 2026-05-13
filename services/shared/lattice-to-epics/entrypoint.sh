#!/bin/bash

echo "Waiting for Comms...";
until $(curl -X GET --output /dev/null --silent --head --fail http://lattice_api:5000/v1/lattice/runs/); do sleep 0.1; done
echo "Comms started...";
echo "Waiting for endpoint population...";
while true; do
    RESPONSE=$(curl -s -f http://lattice_api:5000/v1/lattice/runs/)

    echo "curl -X GET 'http://lattice_api:5000/v1/lattice/runs/'"
    echo "Response: $RESPONSE"

    if [ "$RESPONSE" = "[]" ]; then
        sleep 1
    else
        break
    fi
done

until </dev/tcp/broker/9092; do
  sleep 0.1
done

echo "Kafka broker is ready..."

python3 main.py

