FROM ghcr.io/adb-xkc85723/janus-simcodes:latest

ARG LAURA_LATTICE_REPO=git@gitlab.stfc.ac.uk:xkc85723/laura-lattices.git

ADD API /home/web/webapp

# Consolidate all file operations
RUN mkdir -p /home/web/webapp/Output/CLARA && \
    mkdir -p /home/web/webapp/Output/ISIS && \
    mkdir -p /home/web/webapp/Output/JFEL && \
    chmod -R a+rwX /home/web/webapp/Output/CLARA && \
    chmod -R a+rwX /home/web/webapp/Output/ISIS && \
    chmod -R a+rwX /home/web/webapp/Output/JFEL

WORKDIR /laura
RUN git fetch -a && git checkout fix/split-genesis-line && git pull

WORKDIR /simba
RUN git fetch -a && git checkout feature/split-genesis-line && git pull


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

ADD entrypoint.sh /home/web/webapp/
ADD requirements.txt /home/web/webapp/
RUN pip install -r requirements.txt

ENTRYPOINT ["./entrypoint.sh"]