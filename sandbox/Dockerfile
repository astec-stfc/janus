FROM ghcr.io/adb-xkc85723/janus-base:latest

WORKDIR /pycatap
RUN pip3 install --no-cache-dir -r requirements.txt && \
    pip3 install --no-cache-dir -e .

# Set user and entrypoint
WORKDIR /
RUN useradd -ms /bin/bash janus-developer && \
    mkdir user_setup

USER janus-developer
WORKDIR /home/janus-developer/workspace
ENTRYPOINT ["/bin/bash"]