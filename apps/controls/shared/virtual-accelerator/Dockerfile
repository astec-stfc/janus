FROM python:3.12-slim

RUN apt-get update && apt-get install procps ffmpeg libsm6 libxext6 curl openssh-client git ca-certificates -y

RUN python -m pip install pydantic p4p requests --no-cache-dir

ARG FACILITY
ENV FACILITY=$FACILITY

# Consolidate all git clones into single RUN block + remove .git to save space
WORKDIR /
RUN git clone https://github.com/astec-stfc/sarabi.git
RUN pip install --no-cache-dir -r /sarabi/requirements.txt
RUN mkdir -p /sarabi/yaml/nala

RUN git clone https://github.com/astec-stfc/laura-lattices.git
RUN cp -r "/laura-lattices/${FACILITY}/YAML" /sarabi/yaml/nala

WORKDIR /sarabi
RUN python3.12 render_iocs.py --settings=settings.yaml
RUN python3.12 render_main.py --settings=settings.yaml

WORKDIR /src/app

COPY . .

COPY entrypoint.sh ./entrypoint.sh
RUN chmod a+x ./entrypoint.sh

ENTRYPOINT ["/src/app/entrypoint.sh"]
