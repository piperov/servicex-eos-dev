FROM python:3.13-trixie
WORKDIR /servicex

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake \
    osg-ca-certs \
    xrootd-client \
    && rm -rf /var/lib/apt/lists/*

ENV POETRY_VERSION=2.1.1
RUN pip install --no-cache-dir poetry==$POETRY_VERSION

COPY pyproject.toml pyproject.toml
COPY poetry.lock poetry.lock

RUN poetry config virtualenvs.create false && \
    poetry lock && \
    poetry install --no-root --no-interaction --no-ansi

RUN useradd -ms /bin/bash output -G sudo && passwd -d output || true
RUN useradd -g 0 -ms /bin/bash celery || true
USER celery

ENV PYTHONUNBUFFERED=1

COPY scripts/ ./scripts/
COPY src/ ./
ADD gai.conf /etc/gai.conf

ENV X509_USER_PROXY=/etc/grid-security-ro/x509up
ENV X509_CERT_DIR=/etc/grid-security/certificates

ENV PYTHONPATH=/servicex
ENV XRD_LOGLEVEL=Debug
