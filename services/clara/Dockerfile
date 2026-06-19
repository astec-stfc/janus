FROM ghcr.io/adb-xkc85723/janus-base:latest

ARG LAURA_LATTICE_REPO=git@gitlab.stfc.ac.uk:xkc85723/laura-lattices.git

# use SSH agent forwarding (BuildKit) and ensure host key is known
WORKDIR /pycatap
# Consolidate all git clones into single RUN block + remove .git to save space
RUN --mount=type=ssh bash -lc ' \
ssh-keyscan gitlab.stfc.ac.uk >> /root/.ssh/known_hosts && \
git fetch -a && git checkout feature/nala && git pull \
'
RUN pip install -e .
WORKDIR /laura
# Consolidate all git clones into single RUN block + remove .git to save space
RUN --mount=type=ssh bash -lc ' \
ssh-keyscan gitlab.stfc.ac.uk >> /root/.ssh/known_hosts && \
git fetch -a && git checkout fix/screen-resolve && git pull \
'
RUN pip install -e .
WORKDIR /
RUN --mount=type=ssh bash -lc ' \
mkdir -p /root/.ssh && \
ssh-keyscan gitlab.stfc.ac.uk >> /root/.ssh/known_hosts && \
git clone --branch main ${LAURA_LATTICE_REPO} /laura-lattices \
'

WORKDIR /usr/src/app
COPY . /usr/src/app/
RUN pip install -r ./requirements.txt
ADD ./entrypoint.sh /usr/src/app
ENTRYPOINT ["./entrypoint.sh"]