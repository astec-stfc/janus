FROM ghcr.io/adb-xkc85723/janus-base:latest

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
RUN git fetch -a && git checkout fix/split-genesis-line && git pull
RUN pip install -e . --no-deps
RUN pip install -r requirements_lightweight.txt

WORKDIR /
RUN --mount=type=ssh,required=false bash -lc ' \
case "${LAURA_LATTICE_REPO}" in \
    http://*|https://*) \
        git clone --branch main "${LAURA_LATTICE_REPO}" /laura-lattices ;; \
    git@*|ssh://*) \
        mkdir -p /root/.ssh && \
        ssh-keyscan gitlab.stfc.ac.uk >> /root/.ssh/known_hosts && \
        git clone --branch main "${LAURA_LATTICE_REPO}" /laura-lattices ;; \
    *) \
        echo "Unsupported LAURA_LATTICE_REPO format: ${LAURA_LATTICE_REPO}" && exit 1 ;; \
esac \
'

WORKDIR /usr/src/app
COPY . /usr/src/app/
RUN pip install -r ./requirements.txt
ADD ./entrypoint.sh /usr/src/app
ENTRYPOINT ["./entrypoint.sh"]
