FROM python:3.6-stretch
MAINTAINER Nick Bolten <nbolten@gmail.com>

RUN apt-get update && \
    apt-get install -y \
      fiona \
      libspatialindex4v5 \
      libspatialindex-dev

RUN mkdir -p /www
WORKDIR /www

RUN pip3 install --upgrade pip

COPY requirements.txt .
# FIXME: remove this once osm_humanized_opening_hours is fixed
RUN pip3 install pytz==2017.3 babel==2.5.3 lark-parser==0.5.0
RUN pip3 install -r requirements.txt

COPY accessmapapi ./accessmapapi
COPY runserver.py .

CMD ["python3", "./runserver.py"]
