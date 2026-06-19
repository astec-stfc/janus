FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gpg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0xF23C5A6CF475977595C89F51BA6932366A755776" \
    | gpg --dearmor -o /etc/apt/trusted.gpg.d/deadsnakes.gpg

RUN echo "deb https://ppa.launchpadcontent.net/deadsnakes/ppa/ubuntu jammy main" \
    > /etc/apt/sources.list.d/deadsnakes.list

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-dev \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12

# Make python3.12 the default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 \
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
    pip install --no-cache-dir munch && \
    pip install --no-cache-dir deepdiff>=8.6 && \
    pip install --no-cache-dir tqdm>=4 && \
    pip install --no-cache-dir mpl-axes-aligner>=1.1 && \
    pip install --no-cache-dir pyfftw && \
    pip install --no-cache-dir numba && \
    pip install --no-cache-dir numexpr && \
    pip install --no-cache-dir strawberry-graphql[fastapi]

# Consolidate all git clones into single RUN block + remove .git to save space
RUN --mount=type=ssh bash -lc ' \
mkdir -p /root/.ssh && \
ssh-keyscan gitlab.stfc.ac.uk >> /root/.ssh/known_hosts && \
git clone --branch rm-gpt-opal-for-gh git@gitlab.stfc.ac.uk:xkc85723/simcodes.git && \
git clone --branch feature/nala git@gitlab.stfc.ac.uk:ujo48515/pycatap.git \
'

RUN git clone --branch main https://github.com/astec-stfc/laura.git && \
    git clone --branch main https://github.com/astec-stfc/simba.git && \
    git clone --branch main https://github.com/astec-stfc/laura-lattices.git

# Install all requirements in one block (with .git still present for version detection)
RUN pip install --no-cache-dir -r /simcodes/requirements.txt && \
    pip install --no-cache-dir -r /laura/requirements.txt && \
    pip install --no-cache-dir -r /simba/requirements.txt

ENV VIRTUAL_ENV=/home/web/.venv
RUN /usr/bin/python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"