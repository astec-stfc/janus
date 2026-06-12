# Physics IOCs

## Notes
* docker-compose ports need to be configured to be far away from the default pvaccess port to avoid collisions on the actual controls network 
* in the production version the ports are configured for channel access with an environment variable. It would be nice to be able to set the default pvaccess port to be the channel access port +1 in the docker compose file