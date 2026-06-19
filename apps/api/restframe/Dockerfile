FROM ghcr.io/adb-xkc85723/janus-base:latest

ARG LAURA_LATTICE_REPO=git@gitlab.stfc.ac.uk:xkc85723/laura-lattices.git

ENV RPN_DEFNS="${VIRTUAL_ENV}/lib/python3.10/site-packages/SimCodes/Elegant/defns.rpn"

ADD API /home/web/webapp
ADD docker/ASTRA /opt/ASTRA

# Consolidate all file operations
RUN mkdir -p /home/web/webapp/Output/CLARA && \
    mkdir -p /home/web/webapp/Output/ISIS && \
    chmod -R a+rwX /home/web/webapp/Output/CLARA && \
    chmod -R a+rwX /home/web/webapp/Output/ISIS && \
    chmod -R a+rwX /opt/ASTRA && \
    chmod +x /opt/ASTRA/generator.sh && \
    chmod +x /opt/ASTRA/generator && \
    chmod +x /opt/ASTRA/astra_MPICH2.sh && \
    chmod +x /opt/ASTRA/astra_r62M_Linux_x86_64_MPICH2_1.3.2p1 && \
    chmod +x /opt/ASTRA/Astra

WORKDIR /laura
# Consolidate all git clones into single RUN block + remove .git to save space
RUN --mount=type=ssh bash -lc ' \
ssh-keyscan gitlab.stfc.ac.uk >> /root/.ssh/known_hosts && \
git fetch -a && git checkout fix/screen-resolve && git pull \
'

WORKDIR /simba
# Consolidate all git clones into single RUN block + remove .git to save space
RUN --mount=type=ssh bash -lc ' \
ssh-keyscan gitlab.stfc.ac.uk >> /root/.ssh/known_hosts && \
git fetch -a && git checkout main && git pull \
'

WORKDIR /
RUN --mount=type=ssh bash -lc ' \
mkdir -p /root/.ssh && \
ssh-keyscan gitlab.stfc.ac.uk >> /root/.ssh/known_hosts && \
git clone --branch main ${LAURA_LATTICE_REPO} /laura-lattices \
'

WORKDIR /home/web/webapp
ENV PYTHONPATH=/home/web/webapp
ENV PYTHONUNBUFFERED=1

COPY docker/ASTRA $VIRTUAL_ENV/lib/python3.10/site-packages/SimCodes/ASTRA/
ADD entrypoint.sh /home/web/webapp/

ENTRYPOINT ["./entrypoint.sh"]