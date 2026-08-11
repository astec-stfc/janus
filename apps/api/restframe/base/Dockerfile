FROM ghcr.io/adb-xkc85723/janus-base:latest

RUN apt-get update && apt-get install -y --no-install-recommends  \
    gcc g++ make zlib1g-dev libzstd-dev liblzma-dev libhdf5-dev libaec-dev libgsl-dev libpng-dev libgd-dev liblerc-dev libdeflate-dev libtiff-dev qtbase5-dev libblas-dev liblapack-dev liblapacke-dev libfftw3-dev mpich libmpich-dev build-essential cmake libopenmpi-dev libhdf5-openmpi-dev pkg-config

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

WORKDIR /simcodes/SimCodes

RUN git clone https://github.com/svenreiche/Genesis-1.3-Version4.git &&\
    mkdir Genesis &&\
    cd Genesis &&\
    cmake -DCMAKE_BUILD_TYPE=Release ../Genesis-1.3-Version4 &&\
    make

RUN cp "${VIRTUAL_ENV}/lib/python3.10/site-packages/SimCodes/elegant/bin/Linux-x86_64/elegant" /usr/bin/elegant

ENV RPN_DEFNS="${VIRTUAL_ENV}/lib/python3.10/site-packages/SimCodes/Elegant/defns.rpn"

COPY ASTRA $VIRTUAL_ENV/lib/python3.10/site-packages/SimCodes/ASTRA/

WORKDIR /laura
# Consolidate all git clones into single RUN block + remove .git to save space
RUN git fetch -a && git checkout main && git pull
RUN pip install --no-cache-dir -e . --no-deps
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /
RUN git clone --branch main https://github.com/astec-stfc/simba.git
WORKDIR /simba
RUN git fetch -a && git checkout feature/split-genesis-line && git pull
RUN pip install --no-cache-dir -e . --no-deps
RUN pip install --no-cache-dir -r requirements.txt