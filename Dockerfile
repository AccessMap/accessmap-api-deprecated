FROM python:3.6-stretch
MAINTAINER Nick Bolten <nbolten@gmail.com>

RUN apt-get update && \
    apt-get install -y \
      fiona \
      libsqlite3-mod-spatialite

RUN mkdir -p /www
WORKDIR /www

RUN pip3 install --upgrade pip

COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY accessmapapi ./accessmapapi
COPY runserver.py .

CMD ["python3", "./runserver.py"]
