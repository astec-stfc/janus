FROM ghcr.io/adb-xkc85723/janus-base:latest

RUN apt-get update && apt-get install -y --no-install-recommends  \
    gcc g++ make zlib1g-dev libzstd-dev liblzma-dev libhdf5-dev libaec-dev libgsl-dev libpng-dev libgd-dev liblerc-dev libdeflate-dev libtiff-dev qtbase5-dev libblas-dev liblapack-dev liblapacke-dev libfftw3-dev mpich libmpich-dev

WORKDIR "${VIRTUAL_ENV}/lib/python3.10/site-packages/SimCodes/"

RUN git clone https://github.com/rtsoliday/SDDS.git &&\
    cd SDDS &&\
    make -j$(nproc)

RUN git clone https://github.com/rtsoliday/elegant.git &&\
    cd elegant &&\
    git checkout elegant-2026.1.0 &&\
    export MPI_PATH=/usr/lib64/openmpi && \
    export USE_MPI=1 &&\
    make -j1

RUN cp "${VIRTUAL_ENV}/lib/python3.10/site-packages/SimCodes/elegant/bin/Linux-x86_64/elegant" /usr/bin/elegant

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