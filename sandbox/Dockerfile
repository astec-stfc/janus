FROM ghcr.io/adb-xkc85723/janus-base:latest

ARG LAURA_LATTICE_REPO=git@gitlab.stfc.ac.uk:xkc85723/laura-lattices.git

# Set user and entrypoint
WORKDIR /
RUN useradd -ms /bin/bash janus-developer && \
    mkdir user_setup
RUN --mount=type=ssh bash -lc ' \
mkdir -p /root/.ssh && \
ssh-keyscan gitlab.stfc.ac.uk >> /root/.ssh/known_hosts && \
git clone --branch main ${LAURA_LATTICE_REPO} /laura-lattices \
'
RUN mkdir -p /pycatap /laura /home/janus-developer/workspace/snapshots && \
    chown -R janus-developer:janus-developer /pycatap /laura /laura-lattices /home/janus-developer/workspace && \
    chmod -R a+rwX /home/janus-developer/workspace

USER janus-developer

WORKDIR /pycatap
RUN pip install -e .
WORKDIR /laura
RUN pip install -e .

WORKDIR /home/janus-developer/workspace
ENTRYPOINT ["/bin/bash"]