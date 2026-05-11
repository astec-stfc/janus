FROM ghcr.io/adb-xkc85723/janus-base:latest

RUN apt-get update && apt-get install -y iputils-ping
# set work directory
WORKDIR /usr/src/app
COPY . /usr/src/app/
ADD ./entrypoint.sh /usr/src/app
ENTRYPOINT ["./entrypoint.sh"]