FROM ubuntu:22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-dev \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Make python3.10 the default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1 \
 && update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

RUN useradd -m -d /home/web web && mkdir /home/web/.venv && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      openssh-client \
      build-essential \
      libreadline-dev \
      alien \
      python3-venv \
      mpich \
      libgsl27 \
      libfftw3-mpi3 \
      liblapack3 \
      git \
      iputils-ping  \
      wget \
      procps \
      ffmpeg \
      libsm6 \
      libxext6 \
      ca-certificates \
      pip \
      netcat-traditional \
      libpq-dev \
      curl && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Create User
WORKDIR /

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir requests && \
    pip install --no-cache-dir pyepics && \
    pip install --no-cache-dir numpy && \
    pip install --no-cache-dir pydantic>=2.0 && \
    pip install --no-cache-dir ruamel.yaml && \
    pip install --no-cache-dir scipy && \
    pip install --no-cache-dir kafka-python && \
    pip install --no-cache-dir fastkde && \
    pip install --no-cache-dir mpi4py>=3.0.0 && \
    pip install --no-cache-dir cython && \
    pip install --no-cache-dir cffi && \
    pip install --no-cache-dir fastapi[all] && \
    pip install --no-cache-dir uvicorn[standard] && \
    pip install --no-cache-dir lox && \
    pip install --no-cache-dir pyepics && \
    pip install --no-cache-dir attrs && \
    pip install --no-cache-dir sqlmodel && \
    pip install --no-cache-dir kalepy && \
    pip install --no-cache-dir scipy && \
    pip install --no-cache-dir toml && \
    pip install --no-cache-dir Pillow && \
    pip install --no-cache-dir p4p && \
    pip install --no-cache-dir jupyterlab && \
    pip install --no-cache-dir sqlalchemy && \
    pip install --no-cache-dir psycopg2>=2.9.10 && \
    pip install --no-cache-dir h5py && \
    pip install --no-cache-dir strawberry-graphql[fastapi]

COPY apps/api/restframe/docker/SDDSPython3-5.2.1-1.ubuntu.22.04.x86_64.rpm /home/web/
COPY apps/api/restframe/docker/elegant-2025.2.0-1.ubuntu.22.04.mpich.x86_64.rpm /home/web/

ENV VIRTUAL_ENV=/home/web/.venv
RUN /usr/bin/python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN alien -i /home/web/SDDSPython3-5.2.1-1.ubuntu.22.04.x86_64.rpm && \
    cp -r /usr/local/lib/python3.10/dist-packages/* /home/web/.venv/lib/python3.10/site-packages/ && \
    rm /home/web/SDDSPython3-5.2.1-1.ubuntu.22.04.x86_64.rpm && \
    alien -i /home/web/elegant-2025.2.0-1.ubuntu.22.04.mpich.x86_64.rpm && \
    rm /home/web/elegant-2025.2.0-1.ubuntu.22.04.mpich.x86_64.rpm

# Consolidate all git clones into single RUN block + remove .git to save space
RUN --mount=type=ssh bash -lc ' \
mkdir -p /root/.ssh && \
ssh-keyscan gitlab.stfc.ac.uk >> /root/.ssh/known_hosts && \
git clone --branch rm-gpt-opal-for-gh git@gitlab.stfc.ac.uk:xkc85723/simcodes.git && \
git clone --branch main git@gitlab.stfc.ac.uk:xkc85723/laura.git && \
git clone --branch main git@gitlab.stfc.ac.uk:xkc85723/simba.git && \
git clone --branch main git@gitlab.stfc.ac.uk:xkc85723/laura-lattices.git && \
git clone --branch feature/nala git@gitlab.stfc.ac.uk:ujo48515/pycatap.git \
'

# Install all requirements in one block (with .git still present for version detection)
RUN pip install --no-cache-dir -r /simcodes/requirements.txt && \
    pip install --no-cache-dir -r /laura/requirements.txt && \
    pip install --no-cache-dir -r /simba/requirements.txt
