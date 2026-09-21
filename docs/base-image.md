# Base Image

Building the full `JANUS` stack from scratch can be time consuming, given that it needs
install dependencies for multiple services, including EPICS and RESTFrame. 
To speed up development, a base image is available that contains all the 
dependencies for the shared services. 

This base image is built on top of the `ubuntu:22.04` image and is available on 
GHCR at [janus-base](https://ghcr.io/adb-xkc85723/janus-base). The EPICS image is available
at [janus-epics](https://ghcr.io/adb-xkc85723/janus-epics).