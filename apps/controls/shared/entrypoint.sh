#!/bin/bash 
echo "Waiting for Lattice API...";
until $(curl -X GET --output /dev/null --silent --head --fail http://lattice_api:5000/v1/lattice/sections/names/); do sleep 0.1; done 
echo "Lattice API started...";
echo "Waiting for endpoint population...";
while [ "$(curl -X GET --silent --fail http://lattice_api:5000/v1/lattice/sections/names/)" = "[]" ]; 
do 
    sleep 0.1;
done

echo "Lattice Sections Populated...";


/usr/local/bin/python main.py