FROM python:3.12-slim

RUN apt-get update && apt-get install procps ffmpeg libsm6 libxext6 curl openssh-client git ca-certificates -y

RUN python -m pip install pydantic p4p requests --no-cache-dir

ARG FACILITY
ENV FACILITY=$FACILITY

# Consolidate all git clones into single RUN block + remove .git to save space
RUN --mount=type=ssh bash -lc ' \
mkdir -p /root/.ssh && \
ssh-keyscan gitlab.stfc.ac.uk >> /root/.ssh/known_hosts && \
git clone --branch main git@gitlab.stfc.ac.uk:ujo48515/sarabi.git && \
git clone --branch main git@gitlab.stfc.ac.uk:xkc85723/laura-lattices.git \
'

RUN pip install --no-cache-dir -r /sarabi/requirements.txt

RUN cp -r "/laura-lattices/${FACILITY}/YAML" /sarabi/yaml/nala

WORKDIR /sarabi
RUN python3.12 render_iocs.py --settings=settings.yaml
RUN python3.12 render_main.py --settings=settings.yaml

WORKDIR /src/app

COPY . .

COPY entrypoint.sh ./entrypoint.sh
RUN chmod a+x ./entrypoint.sh

ENTRYPOINT ["/src/app/entrypoint.sh"]
