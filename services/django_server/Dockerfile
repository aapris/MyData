# pull official base image
FROM python:3.9-slim-buster

# set work directory
WORKDIR /app/mydata

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install system dependencies
# https://towardsdatascience.com/a-working-environment-for-geospatial-analysis-with-docker-python-and-postgresql-670c2be58e0a
RUN apt-get update --fix-missing

RUN apt-get install -y \
    wget \
    bzip2 \
    ca-certificates \
    build-essential \
    curl \
    git-core \
    pkg-config \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-virtualenv \
    unzip \
    software-properties-common \
    llvm \
    netcat \
    libpq-dev

# If you need GeoDjango:
RUN apt-get install -y gdal-bin python-gdal python3-gdal

RUN pip install --upgrade pip
COPY ./requirements.txt /app/mydata/requirements.txt
RUN pip install -U -r requirements.txt
COPY ./requirements-dev.txt /app/mydata/requirements-dev.txt
RUN pip install -U -r requirements-dev.txt

# run entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]
