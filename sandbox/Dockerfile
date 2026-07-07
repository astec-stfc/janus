FROM ghcr.io/adb-xkc85723/janus-base:latest

ARG LAURA_LATTICE_REPO=git@gitlab.stfc.ac.uk:xkc85723/laura-lattices.git
ENV VIRTUAL_ENV=/home/web/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ARG FACILITY

# Set user and entrypoint
WORKDIR /
RUN useradd -ms /bin/bash janus-developer && \
    mkdir user_setup && \
    chown -R janus-developer:janus-developer "$VIRTUAL_ENV" && \
    chmod o+rx /home/web && \
    chmod -R a+rX "$VIRTUAL_ENV"
RUN --mount=type=ssh bash -lc ' \
mkdir -p /root/.ssh && \
ssh-keyscan gitlab.stfc.ac.uk >> /root/.ssh/known_hosts && \
git clone --branch main ${LAURA_LATTICE_REPO} /laura-lattices \
'
RUN mkdir -p /laura /home/janus-developer/workspace/snapshots && \
    if [ "$FACILITY" = "clara" ]; then mkdir -p /pycatap && chown janus-developer:janus-developer /pycatap; fi && \
    chown -R janus-developer:janus-developer /laura /laura-lattices /home/janus-developer/workspace && \
    chmod -R a+rwX /home/janus-developer/workspace
# use SSH agent forwarding (BuildKit) and ensure host key is known
RUN --mount=type=ssh bash -lc ' \
mkdir -p /root/.ssh && \
ssh-keyscan gitlab.stfc.ac.uk >> /root/.ssh/known_hosts && \
git clone --branch feature/nala git@gitlab.stfc.ac.uk:ujo48515/pycatap.git /pycatap \
'
WORKDIR /pycatap
RUN "$VIRTUAL_ENV/bin/python" -m pip install -e .
WORKDIR /

RUN chmod -R a+rX /home/web

USER janus-developer
ADD requirements.txt .
RUN "$VIRTUAL_ENV/bin/python" -m pip install -r requirements.txt && \
    "$VIRTUAL_ENV/bin/python" -c "import requests"

WORKDIR /home/janus-developer/workspace
CMD ["/bin/bash"]