FROM ghcr.io/adb-xkc85723/janus-base:latest

ARG LAURA_LATTICE_REPO=git@gitlab.stfc.ac.uk:xkc85723/laura-lattices.git
ARG FACILITY

# Set user and entrypoint
WORKDIR /
RUN --mount=type=ssh bash -lc ' \
mkdir -p /root/.ssh && \
ssh-keyscan gitlab.stfc.ac.uk >> /root/.ssh/known_hosts && \
git clone --branch feature/nala git@gitlab.stfc.ac.uk:ujo48515/pycatap.git \
'
WORKDIR /pycatap
RUN pip install -e .
RUN useradd -ms /bin/bash janus-developer && \
    mkdir user_setup

RUN --mount=type=ssh bash -lc ' \
mkdir -p /root/.ssh && \
ssh-keyscan gitlab.stfc.ac.uk >> /root/.ssh/known_hosts && \
git clone --branch main ${LAURA_LATTICE_REPO} /laura-lattices \
'
RUN mkdir -p /laura /home/janus-developer/workspace/snapshots && \
    if [ "$FACILITY" = "clara" ]; then mkdir -p /pycatap && chown janus-developer:janus-developer /pycatap; fi && \
    chown -R janus-developer:janus-developer /laura /laura-lattices /home/janus-developer/workspace && \
    chmod -R a+rwX /home/janus-developer/workspace

RUN pip install pyepics p4p pydantic numpy ruamel.yaml scipy matplotlib jupyterlab pytest

RUN chmod -R a+rX /home/web

USER janus-developer

WORKDIR /home/janus-developer/workspace
CMD ["/bin/bash"]
