#!/bin/bash
if [ "$DATABASE" = "postgres" ]; then
    echo "Waiting for postgres...";
    while ! nc -z $SQL_HOST $SQL_PORT; do sleep 0.1; done
    echo "postgres started...";
fi

if [ "$USE_RESTFRAME" = "true" ]; then
echo "Waiting for RESTFrame...";
until $(curl -X GET --output /dev/null --silent --head --fail http://${RESTFRAME_HOST:-restframe}:${RESTFRAME_PORT:-8000}/lattice); do sleep 0.1; done
echo "RESTFrame started...";
fi

python3 -m uvicorn main:app --log-level=${log_level} --host 0.0.0.0 --port 5000
