FROM ghcr.io/adb-xkc85723/janus-base:latest

COPY docker/SDDSPython3-5.2.1-1.ubuntu.22.04.x86_64.rpm /home/web/
COPY docker/elegant-2025.2.0-1.ubuntu.22.04.mpich.x86_64.rpm /home/web/

RUN alien -i /home/web/SDDSPython3-5.2.1-1.ubuntu.22.04.x86_64.rpm && \
    SITEPKG=$($VIRTUAL_ENV/bin/python -c "import site; print(site.getsitepackages()[0])") && \
    cp -r /usr/local/lib/python3.12/dist-packages/* "$SITEPKG/" && \
    rm /home/web/SDDSPython3-5.2.1-1.ubuntu.22.04.x86_64.rpm && \
    alien -i /home/web/elegant-2025.2.0-1.ubuntu.22.04.mpich.x86_64.rpm && \
    rm /home/web/elegant-2025.2.0-1.ubuntu.22.04.mpich.x86_64.rpm

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
RUN git fetch -a && git checkout fix/screen-resolve && git pull 

WORKDIR /simba
# Consolidate all git clones into single RUN block + remove .git to save space
RUN git fetch -a && git checkout main && git pull


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

WORKDIR /home/web/webapp
ENV PYTHONPATH=/home/web/webapp
ENV PYTHONUNBUFFERED=1

COPY docker/ASTRA $VIRTUAL_ENV/lib/python3.10/site-packages/SimCodes/ASTRA/
ADD entrypoint.sh /home/web/webapp/

ENTRYPOINT ["./entrypoint.sh"]