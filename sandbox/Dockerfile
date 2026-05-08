FROM python:3.10-slim

# # Add epics - consolidated with apt cleanup
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    openssh-client build-essential libreadline-dev iputils-ping wget git && \
    mkdir /usr/EPICS && \
    cd /usr/EPICS && \
    wget https://epics-controls.org/download/base/base-7.0.8.1.tar.gz && \
    tar -xzf base-7.0.8.1.tar.gz && \
    rm base-7.0.8.1.tar.gz && \
    cd base-7.0.8.1 && \
    make configure && make && \
    cd bin/linux-x86_64 && \
    chmod +x caget camonitor caput cainfo pvget pvput pvmonitor pvinfo pvlist && \
    # Clean up build artifacts
    rm -rf /usr/EPICS/base-7.0.8.1/configure* /usr/EPICS/base-7.0.8.1/src && \
    apt-get remove -y build-essential && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

ENV PATH="/usr/EPICS/base-7.0.8.1/bin/linux-x86_64/:$PATH"

# Create User
WORKDIR /
RUN useradd -ms /bin/bash janus-developer && \
    mkdir user_setup

# Setup Python Virtual Environment
ADD ./requirements.txt ./user_setup/requirements.txt
RUN pip3 install --no-cache-dir -r ./user_setup/requirements.txt

WORKDIR /
RUN --mount=type=ssh bash -lc "mkdir -p /root/.ssh && \
ssh-keyscan gitlab.stfc.ac.uk >> /root/.ssh/known_hosts && \
git clone --branch develop git@gitlab.stfc.ac.uk:ujo48515/pycatap.git"

WORKDIR /pycatap
RUN pip3 install --no-cache-dir -r requirements.txt && \
    pip3 install --no-cache-dir -e .

# Set user and entrypoint
USER janus-developer
WORKDIR /home/janus-developer/workspace
ENTRYPOINT ["/bin/bash"]