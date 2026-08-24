# Switch from 'python:3.10' to standard Ubuntu to align system compiled packages
FROM ubuntu:22.04
WORKDIR /servicex

# Install Python 3.10, system XRootD bindings, and build dependencies natively
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    python3-xrootd \
    xrootd-client \
    && rm -rf /var/lib/apt/lists/*

# Symlink python to point directly to python3
RUN ln -s /usr/bin/python3 /usr/bin/python

RUN python3 -m pip install --upgrade pip

ENV POETRY_VERSION=2.1.1
RUN pip install poetry==$POETRY_VERSION

COPY pyproject.toml pyproject.toml
COPY poetry.lock poetry.lock

# Sync your Python packages natively via Poetry into the system environment
RUN poetry config virtualenvs.create false && \
    poetry lock && \
    poetry install --no-root --no-interaction --no-ansi

RUN useradd -ms /bin/bash output -G sudo && passwd -d output
RUN chgrp -R 0 /home/output && chmod -R g+rwX /home/output
RUN useradd -g 0 -ms /bin/bash celery
USER celery

ENV PYTHONUNBUFFERED=1

COPY scripts/ ./scripts/
COPY src/ ./
ADD gai.conf /etc/gai.conf

ENV X509_USER_PROXY=/tmp/grid-security/x509up
ENV X509_CERT_DIR=/etc/grid-security/certificates

# Set your PYTHONPATH to the unified system location
ENV PYTHONPATH=/servicex:/usr/lib/python3/dist-packages

