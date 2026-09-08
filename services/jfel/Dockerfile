FROM ghcr.io/adb-xkc85723/janus-base:latest


ARG LAURA_VERSION=v1.0.0
ARG LAURA_LATTICES_VERSION=v0.1.0
ARG LAURA_LATTICE_REPO=git@gitlab.stfc.ac.uk:xkc85723/laura-lattices.git
ARG ACRONICTA_CATAP_REPO=https://github.coom/astec-stfc/acronicta-catap.git
ARG ACRONICTA_CATAP_VERSION=v0.1.0

RUN apt-get update && apt-get install -y black flake8

WORKDIR /laura
# different checkout behaviour for tags vs branches, so check if the tag exists first
RUN git fetch --all --tags && \
    if git rev-parse --verify "refs/tags/${LAURA_VERSION}" >/dev/null 2>&1; then \
        git checkout --detach "${LAURA_VERSION}"; \
    else \
        git checkout --detach "origin/${LAURA_VERSION}"; \
    fi

WORKDIR /
RUN --mount=type=ssh,required=false bash -lc ' \
case "${LAURA_LATTICE_REPO}" in \
    http://*|https://*) \
        git clone --branch "${LAURA_LATTICES_VERSION}" "${LAURA_LATTICE_REPO}" /laura-lattices ;; \
    git@*|ssh://*) \
        mkdir -p /root/.ssh && \
        ssh-keyscan gitlab.stfc.ac.uk >> /root/.ssh/known_hosts && \
        git clone --branch "${LAURA_LATTICES_VERSION}" "${LAURA_LATTICE_REPO}" /laura-lattices ;; \
    *) \
        echo "Unsupported LAURA_LATTICE_REPO format: ${LAURA_LATTICE_REPO}" && exit 1 ;; \
esac \
'
WORKDIR /laura
RUN python -m pip install -r requirements.txt
RUN python -m pip install -e .

WORKDIR /usr/src/app
RUN python -m pip install --upgrade pip
COPY ./requirements.txt /usr/src/app/requirements.txt
RUN python -m pip install -r requirements.txt

WORKDIR /
RUN git clone --recursive --branch "${ACRONICTA_CATAP_VERSION}" "${ACRONICTA_CATAP_REPO}" /acronicta-catap
WORKDIR /acronicta-catap
RUN pip install -r requirements.txt

RUN python3 /acronicta-catap/scripts/generate_hardware.py --yaml_location=/laura-lattices/JFEL/YAML/ --output_location=/acronicta-catap/facility/jfel --overwrite_hardware

WORKDIR /usr/src/app
COPY . /usr/src/app/
ADD ./entrypoint.sh /usr/src/app
RUN chmod a+x /usr/src/app/entrypoint.sh
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]