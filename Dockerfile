FROM ubuntu:16.04
MAINTAINER Nick Bolten <nbolten@gmail.com>

RUN apt-get update && \
    apt-get install -y \
      libpq-dev \
      python3-pip

RUN mkdir -p /docker-entrypoint-accessmapapi/accessmapapi
WORKDIR /docker-entrypoint-accessmapapi

COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY accessmapapi ./accessmapapi
COPY runserver.py .

EXPOSE 5555

CMD ["python3", "./runserver.py"]
