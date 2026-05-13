# pull python base image
FROM python:3.10

# set work directory
WORKDIR /usr/src/app

# environment variables set
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DATABASE postgres
ENV USE_RESTFRAME true

# install system deps
RUN apt-get update && apt-get install -y netcat-traditional

# install python deps
RUN pip install --upgrade pip
RUN pip install --upgrade wheel 
RUN pip install --upgrade setuptools
COPY ./requirements.txt /usr/src/app/requirements.txt
RUN pip install -r requirements.txt
COPY . /usr/src/app/
ADD ./entrypoint.sh /usr/src/app
ENTRYPOINT ["./entrypoint.sh"]