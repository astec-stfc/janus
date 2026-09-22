FROM python:3.12-slim

RUN apt-get update && apt-get install procps ffmpeg libsm6 libxext6 curl openssh-client git ca-certificates -y

RUN python -m pip install pydantic p4p requests --no-cache-dir

ARG LAURA_LATTICE_REPO=https://github.com/astec-stfc/laura-lattices.git
ARG LAURA_LATTICES_VERSION=v0.1.2
ARG LAURA_REPO=https://github.com/astec-stfc/laura.git
ARG LAURA_VERSION=v1.0.0
ARG SARABI_REPO=https://github.com/astec-stfc/sarabi.git
ARG SARABI_VERSION=v0.1.0
ARG FACILITY
ENV FACILITY=$FACILITY
ENV LAURA_LATTICE_REPO=$LAURA_LATTICE_REPO
ENV LAURA_LATTICES_VERSION=$LAURA_LATTICES_VERSION
ENV LAURA_REPO=$LAURA_REPO
ENV LAURA_VERSION=$LAURA_VERSION
ENV SARABI_REPO=$SARABI_REPO
ENV SARABI_VERSION=$SARABI_VERSION


RUN git clone --branch "${SARABI_VERSION}" "${SARABI_REPO}" /sarabi

RUN git clone --branch "${LAURA_VERSION}" "${LAURA_REPO}" /laura

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
RUN pip install --no-cache-dir -e /laura

RUN pip install --no-cache-dir -r /sarabi/requirements.txt

RUN mkdir -p /sarabi/yaml && cp -r "/laura-lattices/${FACILITY}/YAML" /sarabi/yaml/${FACILITY}

# Replace @FACILITY@ placeholder in settings.yaml with the actual facility name
COPY settings.yaml /sarabi/settings.yaml
RUN sed "s|@FACILITY@|${FACILITY}|g" /sarabi/settings.yaml > /tmp/settings.yaml && \
    mv /tmp/settings.yaml /sarabi/settings.yaml

WORKDIR /sarabi
RUN python3.12 render_iocs.py --settings=settings.yaml
RUN python3.12 render_main.py --settings=settings.yaml

COPY . src/app

WORKDIR src/app

ADD entrypoint.sh /usr/src/app/entrypoint.sh
RUN chmod a+x /usr/src/app/entrypoint.sh
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
