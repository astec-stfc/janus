FROM python:3.12-bookworm

RUN apt-get update && apt-get install -y curl

# set work directory
WORKDIR /usr/src/app

# install python deps
RUN pip install --upgrade pip
COPY ./requirements.txt /usr/src/app/requirements.txt
RUN pip install -r requirements.txt
COPY . /usr/src/app/
COPY ./entrypoint.sh /usr/src/app
ENTRYPOINT ["./entrypoint.sh"]