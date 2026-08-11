FROM python:3.11-slim
RUN apt-get update && apt-get install -y curl
RUN pip install hsds

COPY config.yml /config/config.yml
COPY passwd.txt /config/passwd.txt

RUN mkdir -p /hsds-store

CMD ["hsds","--root_dir", "/hsds-store", "--config_dir", "/config"]