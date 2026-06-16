FROM ghcr.io/adb-xkc85723/janus-base:latest

RUN apt-get update && apt-get install -y black flake8

WORKDIR /laura
# Consolidate all git clones into single RUN block
RUN git fetch -a && git checkout fix/split-genesis-line && git pull
RUN pip install -e .

WORKDIR /laura-lattices
RUN git fetch -a && git checkout main && git pull

RUN pip install --upgrade flask black pytest

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