FROM python:3.12-slim

RUN apt-get update && apt-get install procps ffmpeg libsm6 libxext6 curl openssh-client git ca-certificates -y

RUN python -m pip install pydantic p4p requests --no-cache-dir

ARG LAURA_LATTICE_REPO=git@gitlab.stfc.ac.uk:xkc85723/laura-lattices.git
ARG FACILITY
ENV FACILITY=$FACILITY
ENV LAURA_LATTICE_REPO=$LAURA_LATTICE_REPO

# Consolidate all git clones into single RUN block + remove .git to save space
RUN git clone --branch main https://github.com/astec-stfc/sarabi.git

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

RUN pip install --no-cache-dir -r /sarabi/requirements.txt

RUN mkdir -p /sarabi/yaml && cp -r "/laura-lattices/${FACILITY}/YAML" /sarabi/yaml/nala

WORKDIR /sarabi
RUN python3.12 render_iocs.py --settings=settings.yaml
RUN python3.12 render_main.py --settings=settings.yaml

COPY . src/app

WORKDIR src/app

ADD entrypoint.sh /usr/src/app/ioc_entrypoint.sh
RUN chmod a+x /usr/src/app/ioc_entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
