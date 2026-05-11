FROM ghcr.io/adb-xkc85723/janus-base:latest

# set work directory
WORKDIR /usr/src/app
COPY . /usr/src/app/
COPY ./entrypoint.sh /usr/src/app
ENTRYPOINT ["./entrypoint.sh"]