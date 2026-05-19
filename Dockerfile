# SPDX-FileCopyrightText: 2023-2026 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

FROM python:3.11-bookworm AS python

ARG DOCKER_VERSION=24.0.2
ARG DOCKER_COMPOSE_VERSION=2.20.0

COPY --from=ghcr.io/astral-sh/uv:0.11.15 /uv /usr/local/bin/uv

ENV UV_SYSTEM_PYTHON=1 \
    UV_NO_CACHE=1 \
    PATH="/platform/.venv/bin:$PATH"

# Install dependencies for nbconvert
RUN apt-get update && \
    apt-get install --yes --no-install-recommends \
    texlive-xetex texlive-fonts-recommended texlive-plain-generic \
    pandoc \
    libgraphviz-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Minio CLI client
RUN curl --create-dirs -fsSL https://dl.min.io/client/mc/release/linux-amd64/mc -o /usr/local/bin/mc && \
    chmod +x /usr/local/bin/mc

# Install Docker CLI client
RUN curl -fsSLO https://download.docker.com/linux/static/stable/x86_64/docker-${DOCKER_VERSION}.tgz \
    && tar xzvf docker-${DOCKER_VERSION}.tgz --strip 1 \
    -C /usr/local/bin docker/docker \
    && rm docker-${DOCKER_VERSION}.tgz

# Install Docker Compose CLI client
RUN mkdir -p /root/.docker/cli-plugins && \
    curl --create-dirs -fsSL https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-linux-x86_64 -o /root/.docker/cli-plugins/docker-compose && \
    chmod +x /root/.docker/cli-plugins/docker-compose

RUN mkdir /platform
WORKDIR /platform
COPY README.md uv.lock pyproject.toml /platform/

# Only install dependencies here to improve utilization of layer cache
RUN uv sync --no-dev --no-install-project

COPY seguro /platform/seguro

# Install the seguro package
RUN uv sync --no-dev

FROM debian:bookworm AS setup

RUN apt-get update && \
    apt-get install --yes --no-install-recommends \
    openssh-client \
    apache2-utils \
    openssl \
    curl \
    ca-certificates && \
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

CMD ["/bin/bash", "-c", "while sleep 1000; do :; done"]

FROM python
