FROM ghcr.io/adb-xkc85723/janus-base:latest

# set work directory
COPY . /usr/src/app/
ADD ./entrypoint.sh /usr/src/app
ENTRYPOINT ["./entrypoint.sh"]