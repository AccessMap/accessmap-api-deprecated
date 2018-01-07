FROM python:3.6-stretch
MAINTAINER Nick Bolten <nbolten@gmail.com>

RUN apt-get update && \
    apt-get install -y \
      fiona \
      libspatialindex4v5 \
      libspatialindex-dev

RUN mkdir -p /www
WORKDIR /www

COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY accessmapapi ./accessmapapi
COPY runserver.py .

CMD ["python3", "./runserver.py"]
