#!/bin/bash
echo "Waiting for Comms...";
until $(curl -X GET --output /dev/null --silent --head --fail http://lattice_api:5000/v1/lattice/sections/names/); do sleep 0.1; done
echo "Comms started...";
echo "Waiting for endpoint population...";
while [ "$(curl -X GET --silent --fail http://lattice_api:5000/v1/lattice/sections/names/)" = "[]" ]; 
do 
    sleep 0.1;
done
echo "endpoint available...";
until </dev/tcp/broker/9092; do
  sleep 0.1
done

echo "Kafka broker is ready..."
python3 main.py
