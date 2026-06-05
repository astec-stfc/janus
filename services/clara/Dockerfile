FROM ghcr.io/adb-xkc85723/janus-base:latest

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
WORKDIR /laura-lattices
# Consolidate all git clones into single RUN block + remove .git to save space
RUN --mount=type=ssh bash -lc ' \
ssh-keyscan gitlab.stfc.ac.uk >> /root/.ssh/known_hosts && \
git fetch -a && git checkout main && git pull \
'

WORKDIR /usr/src/app
COPY . /usr/src/app/
ADD ./entrypoint.sh /usr/src/app
ENTRYPOINT ["./entrypoint.sh"]