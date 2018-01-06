FROM ubuntu:16.04
MAINTAINER Nick Bolten <nbolten@gmail.com>

RUN apt-get update && \
    apt-get install -y \
      python3-pip

# pip8 sucks - use 9
RUN pip install --upgrade pip

RUN mkdir -p /www
WORKDIR /www

COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY accessmapapi ./accessmapapi
COPY runserver.py .

CMD ["python3", "./runserver.py"]
