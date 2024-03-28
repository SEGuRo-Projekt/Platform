# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

FROM python:3.11-bookworm AS python

ARG DOCKER_COMPOSE_VERSION=v2.20.0

ENV POETRY_NO_INTERACTION=1 \
   POETRY_VIRTUALENVS_CREATE=false \
   POETRY_CACHE_DIR='/var/cache/pypoetry' \
   POETRY_HOME='/usr/local' \
   POETRY_VERSION=1.7.1

# Install Minio client
RUN curl --create-dirs -fsSL https://dl.min.io/client/mc/release/linux-amd64/mc -o /usr/local/bin/mc && \
    chmod +x /usr/local/bin/mc

# Install Docker Compose
RUN curl --create-dirs -fsSL https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose && \
    chmod +x /usr/local/bin/docker-compose

# Install Poetry
RUN pip install --no-cache-dir poetry==${POETRY_VERSION}

RUN mkdir /platform
WORKDIR /platform
COPY README.md poetry.lock pyproject.toml /platform/
COPY seguro /platform/seguro

RUN poetry install --without docs


FROM debian:bookworm AS setup

RUN apt-get update && \
    apt-get install --yes --no-install-recommends \
    openssh-client \
    apache2-utils \
    openssl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENTRYPOINT [ "/bin/bash" ]

FROM python AS dev-vscode

RUN apt-get update && \
    apt-get install --yes --no-install-recommends \
    sudo \
    bash-completion \
    mosquitto-clients && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Docker CLI
ARG DOCKER_VERSION=24.0.2
RUN curl -fsSLO https://download.docker.com/linux/static/stable/x86_64/docker-${DOCKER_VERSION}.tgz \
    && tar xzvf docker-${DOCKER_VERSION}.tgz --strip 1 \
    -C /usr/local/bin docker/docker \
    && rm docker-${DOCKER_VERSION}.tgz

CMD ["/bin/bash", "-c", "while sleep 1000; do :; done"]

FROM python
