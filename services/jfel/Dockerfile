FROM ghcr.io/adb-xkc85723/janus-base:latest

RUN apt-get update && apt-get install -y black flake8

WORKDIR /laura
# Consolidate all git clones into single RUN block
RUN git fetch -a && git checkout fix/split-genesis-line && git pull
RUN pip install -e .

ARG LAURA_LATTICE_REPO=git@gitlab.stfc.ac.uk:xkc85723/laura-lattices.git

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

WORKDIR /usr/src/app
RUN python -m pip install --upgrade pip
COPY ./requirements.txt /usr/src/app/requirements.txt
RUN python -m pip install -r requirements.txt

WORKDIR /
RUN git clone --branch feature/aliases https://github.com/astec-stfc/acronicta-catap.git
WORKDIR /acronicta-catap
RUN git clone --branch feature/aliases https://github.com/astec-stfc/catapcore.git
RUN pip install -r requirements.txt

RUN python3 /acronicta-catap/scripts/generate_hardware.py --yaml_location=/laura-lattices/JFEL/YAML/ --output_location=/acronicta-catap/facility/jfel --overwrite_hardware

WORKDIR /usr/src/app
COPY . /usr/src/app/
ADD ./entrypoint.sh /usr/src/app
RUN chmod a+x /usr/src/app/entrypoint.sh
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]