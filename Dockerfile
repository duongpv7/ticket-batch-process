FROM python:3.8

RUN apt-get update && apt-get -y upgrade
RUN apt-get -y install libpq-dev gcc nano

RUN mkdir src

ADD requirements.txt requirements.txt
COPY src src

RUN pip install -r requirements.txt