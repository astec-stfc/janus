FROM ubuntu:22.04

RUN useradd -m -d /home/web web && mkdir /home/web/.venv && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      openssh-client alien python3-venv mpich libgsl27 libfftw3-mpi3 liblapack3 git && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV=/home/web/.venv
RUN /usr/bin/python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir fastkde==1.0.30 mpi4py

COPY docker/SDDSPython3-5.2.1-1.ubuntu.22.04.x86_64.rpm /home/web/
COPY docker/elegant-2025.2.0-1.ubuntu.22.04.mpich.x86_64.rpm /home/web/

RUN alien -i /home/web/SDDSPython3-5.2.1-1.ubuntu.22.04.x86_64.rpm && \
    cp -r /usr/local/lib/python3.10/dist-packages/* /home/web/.venv/lib/python3.10/site-packages/ && \
    rm /home/web/SDDSPython3-5.2.1-1.ubuntu.22.04.x86_64.rpm && \
    alien -i /home/web/elegant-2025.2.0-1.ubuntu.22.04.mpich.x86_64.rpm && \
    rm /home/web/elegant-2025.2.0-1.ubuntu.22.04.mpich.x86_64.rpm

RUN pip install --no-cache-dir \
  cython cffi fastapi "uvicorn[standard]" "fastkde<2" "numpy<2" lox pyepics attrs sqlmodel kalepy "scipy<1.14.0" toml kafka-python

# Consolidate all git clones into single RUN block + remove .git to save space
RUN --mount=type=ssh bash -lc ' \
mkdir -p /root/.ssh && \
ssh-keyscan gitlab.stfc.ac.uk >> /root/.ssh/known_hosts && \
git clone --branch rm-gpt-opal-for-gh git@gitlab.stfc.ac.uk:xkc85723/simcodes.git && \
git clone --branch main git@gitlab.stfc.ac.uk:xkc85723/laura.git && \
git clone --branch main git@gitlab.stfc.ac.uk:xkc85723/simba.git && \
git clone --branch main git@gitlab.stfc.ac.uk:xkc85723/laura-lattices.git \
'

# Install all requirements in one block (with .git still present for version detection)
RUN pip install --no-cache-dir -r /simcodes/requirements.txt && pip install --no-cache-dir -e /simcodes && \
    pip install --no-cache-dir -r /laura/requirements.txt && pip install --no-cache-dir -e /laura && \
    pip install --no-cache-dir -r /simba/requirements.txt && pip install --no-cache-dir -e /simba && \
    rm -rf /simcodes/.git /laura/.git /simba/.git /laura-lattices/.git

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


WORKDIR /home/web/webapp
ENV PYTHONPATH=/home/web/webapp
ENV PYTHONUNBUFFERED=1

COPY docker/ASTRA $VIRTUAL_ENV/lib/python3.10/site-packages/SimCodes/ASTRA/
ADD ./entrypoint.sh /home/web/webapp/

ENTRYPOINT ["./entrypoint.sh"]