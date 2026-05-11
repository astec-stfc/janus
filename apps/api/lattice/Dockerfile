# pull python base image
FROM ghcr.io/adb-xkc85723/janus-base:latest

# set work directory
WORKDIR /usr/src/app

# environment variables set
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DATABASE postgres
ENV USE_RESTFRAME true

COPY . /usr/src/app/
ADD ./entrypoint.sh /usr/src/app
ENTRYPOINT ["./entrypoint.sh"]