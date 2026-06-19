#!/bin/bash 
echo "Waiting for Lattice API...";
until $(curl -X GET --output /dev/null --silent --head --fail http://${LATTICE_API_HOST:-lattice_api}:${LATTICE_API_PORT:-5000}/v1/lattice/sections/names/); do sleep 0.1; done 
echo "Lattice API started...";
echo "Waiting for endpoint population...";
while [ "$(curl -X GET --silent --fail http://${LATTICE_API_HOST:-lattice_api}:${LATTICE_API_PORT:-5000}/v1/lattice/sections/names/)" = "[]" ]; 
do 
    sleep 0.1;
done

echo "Lattice Sections Populated...";


python3 main.py
