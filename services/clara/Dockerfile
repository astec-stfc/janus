FROM ghcr.io/adb-xkc85723/janus-base:latest

ARG LAURA_VERSION=v1.0.0
ARG LAURA_LATTICES_VERSION=v0.1.0
ARG LAURA_LATTICE_REPO=git@gitlab.stfc.ac.uk:xkc85723/laura-lattices.git
# use SSH agent forwarding (BuildKit) and ensure host key is known
RUN --mount=type=ssh bash -lc ' \
mkdir -p /root/.ssh && \
ssh-keyscan gitlab.stfc.ac.uk >> /root/.ssh/known_hosts && \
git clone --branch feature/nala git@gitlab.stfc.ac.uk:ujo48515/pycatap.git /pycatap \
'
WORKDIR /pycatap
RUN pip install -e .

WORKDIR /laura
# different checkout behaviour for tags vs branches, so check if the tag exists first
RUN git fetch --all --tags && \
    if git rev-parse --verify "refs/tags/${LAURA_VERSION}" >/dev/null 2>&1; then \
        git checkout --detach "${LAURA_VERSION}"; \
    else \
        git checkout --detach "origin/${LAURA_VERSION}"; \
    fi

RUN pip install -e .

WORKDIR /
RUN --mount=type=ssh,required=false bash -lc ' \
case "${LAURA_LATTICE_REPO}" in \
    http://*|https://*) \
        git clone --branch "${LAURA_LATTICES_VERSION}" "${LAURA_LATTICE_REPO}" /laura-lattices ;; \
    git@*|ssh://*) \
        mkdir -p /root/.ssh && \
        ssh-keyscan gitlab.stfc.ac.uk >> /root/.ssh/known_hosts && \
        git clone --branch "${LAURA_LATTICES_VERSION}" "${LAURA_LATTICE_REPO}" /laura-lattices ;; \
    *) \
        echo "Unsupported LAURA_LATTICE_REPO format: ${LAURA_LATTICE_REPO}" && exit 1 ;; \
esac \
'

WORKDIR /usr/src/app
COPY . /usr/src/app/
RUN pip install -r ./requirements.txt
ADD ./entrypoint.sh /usr/src/app
ENTRYPOINT ["./entrypoint.sh"]
