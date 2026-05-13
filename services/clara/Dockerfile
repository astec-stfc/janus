FROM python:3.11

# set work directory
WORKDIR /usr/src/app

# install python deps
RUN python -m pip install --upgrade pip
COPY ./requirements.txt /usr/src/app/requirements.txt
RUN python -m pip install -r requirements.txt
# RUN #pip3 install --extra-index-url http://apclara1.dl.ac.uk:8090/simple/ --trusted-host apclara1.dl.ac.uk pyCATAP
WORKDIR /
RUN apt-get update && apt-get install -y --no-install-recommends git openssh-client ca-certificates && rm -rf /var/lib/apt/lists/*
# use SSH agent forwarding (BuildKit) and ensure host key is known
RUN --mount=type=ssh bash -lc "mkdir -p /root/.ssh && \
ssh-keyscan gitlab.stfc.ac.uk >> /root/.ssh/known_hosts && \
git clone --branch feature/nala git@gitlab.stfc.ac.uk:ujo48515/pycatap.git"
WORKDIR /pycatap
RUN pip install -r requirements.txt
RUN pip install -e .
WORKDIR /
RUN --mount=type=ssh bash -lc "mkdir -p /root/.ssh && \
ssh-keyscan gitlab.stfc.ac.uk >> /root/.ssh/known_hosts && \
git clone --branch main git@gitlab.stfc.ac.uk:xkc85723/laura.git"
WORKDIR /laura
RUN pip install -r requirements.txt
RUN pip install -e .
WORKDIR /
RUN --mount=type=ssh bash -lc "mkdir -p /root/.ssh && \
ssh-keyscan gitlab.stfc.ac.uk >> /root/.ssh/known_hosts && \
git clone --branch main git@gitlab.stfc.ac.uk:xkc85723/laura-lattices.git"

WORKDIR /usr/src/app
COPY . /usr/src/app/
ADD ./entrypoint.sh /usr/src/app
ENTRYPOINT ["./entrypoint.sh"]