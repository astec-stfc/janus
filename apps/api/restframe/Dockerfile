FROM ghcr.io/adb-xkc85723/janus-base:latest

COPY docker/SDDSPython3-5.2.1-1.ubuntu.22.04.x86_64.rpm /home/web/
COPY docker/elegant-2025.2.0-1.ubuntu.22.04.mpich.x86_64.rpm /home/web/

RUN alien -i /home/web/SDDSPython3-5.2.1-1.ubuntu.22.04.x86_64.rpm && \
    SITEPKG=$($VIRTUAL_ENV/bin/python -c "import site; print(site.getsitepackages()[0])") && \
    cp -r /usr/local/lib/python3.12/dist-packages/* "$SITEPKG/" && \
    rm /home/web/SDDSPython3-5.2.1-1.ubuntu.22.04.x86_64.rpm && \
    alien -i /home/web/elegant-2025.2.0-1.ubuntu.22.04.mpich.x86_64.rpm && \
    rm /home/web/elegant-2025.2.0-1.ubuntu.22.04.mpich.x86_64.rpm

ENV RPN_DEFNS="${VIRTUAL_ENV}/lib/python3.10/site-packages/SimCodes/Elegant/defns.rpn"

ADD API /home/web/webapp
ADD docker/ASTRA /opt/ASTRA

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      cmake \
      git \
      libopenmpi-dev \
      libhdf5-openmpi-dev \
      pkg-config \
      libfftw3-dev

WORKDIR /simcodes/SimCodes

RUN git clone https://github.com/svenreiche/Genesis-1.3-Version4.git Genesis
RUN mkdir Genesis/build && \
    cd Genesis/build && \
    cmake -DCMAKE_BUILD_TYPE=Release .. && \
    make && \
    cp genesis4 ..

# Consolidate all file operations
RUN mkdir -p /home/web/webapp/Output/CLARA && \
    mkdir -p /home/web/webapp/Output/ISIS && \
    mkdir -p /home/web/webapp/Output/JFEL && \
    chmod -R a+rwX /home/web/webapp/Output/CLARA && \
    chmod -R a+rwX /home/web/webapp/Output/ISIS && \
    chmod -R a+rwX /home/web/webapp/Output/JFEL && \
    chmod -R a+rwX /opt/ASTRA && \
    chmod +x /opt/ASTRA/generator.sh && \
    chmod +x /opt/ASTRA/generator && \
    chmod +x /opt/ASTRA/astra_MPICH2.sh && \
    chmod +x /opt/ASTRA/astra_r62M_Linux_x86_64_MPICH2_1.3.2p1 && \
    chmod +x /opt/ASTRA/Astra

WORKDIR /laura
RUN git fetch -a && git checkout fix/split-genesis-line && git pull

WORKDIR /simba
RUN git fetch -a && git checkout feature/split-genesis-line && git pull

WORKDIR /laura-lattices
RUN git fetch -a && git checkout main && git pull

WORKDIR /home/web/webapp
ENV PYTHONPATH=/home/web/webapp
ENV PYTHONUNBUFFERED=1

COPY docker/ASTRA $VIRTUAL_ENV/lib/python3.10/site-packages/SimCodes/ASTRA/
ADD entrypoint.sh /home/web/webapp/

ENTRYPOINT ["./entrypoint.sh"]