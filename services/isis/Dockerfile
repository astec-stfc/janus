FROM python:3.11

RUN apt-get update && apt-get install -y iputils-ping

# set work directory
WORKDIR /usr/src/app

# install python deps
RUN python -m pip install --upgrade pip
COPY ./requirements.txt /usr/src/app/requirements.txt
RUN python -m pip install -r requirements.txt
COPY . /usr/src/app/
ADD ./entrypoint.sh /usr/src/app
ENTRYPOINT ["./entrypoint.sh"]