FROM ghcr.io/adb-xkc85723/janus-base:latest

ENV VIRTUAL_ENV=/home/web/.venv
RUN /usr/bin/python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY docker/SDDSPython3-5.2.1-1.ubuntu.22.04.x86_64.rpm /home/web/
COPY docker/elegant-2025.2.0-1.ubuntu.22.04.mpich.x86_64.rpm /home/web/

RUN alien -i /home/web/SDDSPython3-5.2.1-1.ubuntu.22.04.x86_64.rpm && \
    cp -r /usr/local/lib/python3.10/dist-packages/* /home/web/.venv/lib/python3.10/site-packages/ && \
    rm /home/web/SDDSPython3-5.2.1-1.ubuntu.22.04.x86_64.rpm && \
    alien -i /home/web/elegant-2025.2.0-1.ubuntu.22.04.mpich.x86_64.rpm && \
    rm /home/web/elegant-2025.2.0-1.ubuntu.22.04.mpich.x86_64.rpm

ENV ENV RPN_DEFNS="${VIRTUAL_ENV}/lib/python3.10/site-packages/SimCodes/Elegant/defns.rpn"

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
git fetch -a && git checkout main && git pull \
'


WORKDIR /home/web/webapp
ENV PYTHONPATH=/home/web/webapp
ENV PYTHONUNBUFFERED=1

COPY docker/ASTRA $VIRTUAL_ENV/lib/python3.10/site-packages/SimCodes/ASTRA/
ADD entrypoint.sh /home/web/webapp/

ENTRYPOINT ["./entrypoint.sh"]