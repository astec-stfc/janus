FROM ghcr.io/adb-xkc85723/janus-base:latest

# Set user and entrypoint
WORKDIR /
RUN useradd -ms /bin/bash janus-developer && \
    mkdir user_setup
RUN mkdir -p /pycatap /laura /laura-lattices /home/janus-developer/workspace/snapshots && \
    chown -R janus-developer:janus-developer /pycatap /laura /laura-lattices /home/janus-developer/workspace && \
    chmod -R a+rwX /home/janus-developer/workspace

USER janus-developer

WORKDIR /pycatap
RUN pip install -e .
WORKDIR /laura
RUN pip install -e .

WORKDIR /home/janus-developer/workspace
ENTRYPOINT ["/bin/bash"]