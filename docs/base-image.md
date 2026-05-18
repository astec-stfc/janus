JANUS - Base Image
==================

Building the full `JANUS` stack from scratch can be time consuming, given that it needs
install dependencies for multiple services, including EPICS and RESTFrame. 
To speed up development, a base image is available that contains all the 
dependencies for the shared services. 

This base image is built on top of the `ubuntu:22.04` image and is available on 
Docker Hub at [janus-base](ghcr.io/adb-xkc85723/janus-base:latest). The EPICS image is available
at [janus-epics](ghcr.io/adb-xkc85723/janus-epics:latest).