FROM ghcr.io/adb-xkc85723/janus-base:latest

ARG LAURA_LATTICE_REPO=https://github.com/astec-stfc/laura-lattices.git
ARG LAURA_LATTICES_VERSION=v0.1.2
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
git clone --branch ${LAURA_LATTICES_VERSION} ${LAURA_LATTICE_REPO} /laura-lattices \
'

WORKDIR /

RUN chmod -R a+rX /home/web

USER janus-developer
ADD requirements.txt .
RUN "$VIRTUAL_ENV/bin/python" -m pip install -r requirements.txt && \
    "$VIRTUAL_ENV/bin/python" -c "import requests"

WORKDIR /home/janus-developer/workspace
CMD ["/bin/bash"]