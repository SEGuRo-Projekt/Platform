# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

FROM python:3.11-bookworm AS python

COPY requirements.txt /

RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml /
COPY seguro /seguro
RUN pip install --no-cache-dir /


FROM golang:1.20-alpine as go-builder
RUN  go install github.com/minio/mc@latest

FROM python AS minio-setup

COPY --from=go-builder /go/bin/mc /usr/bin/mc

RUN apt-get update && \
    apt-get install --yes --no-install-recommends \
        openssh-client=1:9.2p1-2 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


FROM python AS dev-vscode

# create a non-root user for vscode to use
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN apt-get update && \
    apt-get install --yes --no-install-recommends \
        sudo=1.9.13p3-1 \
        bash-completion=1:2.11-6 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Docker CLI
ARG DOCKER_VERSION=24.0.2
RUN curl -fsSLO https://download.docker.com/linux/static/stable/x86_64/docker-${DOCKER_VERSION}.tgz \
  && tar xzvf docker-${DOCKER_VERSION}.tgz --strip 1 \
                 -C /usr/local/bin docker/docker \
  && rm docker-${DOCKER_VERSION}.tgz

RUN groupadd --gid $USER_GID $USERNAME && \
    useradd --uid $USER_UID --gid $USER_GID -m $USERNAME && \
    echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME && \
    chmod 0440 /etc/sudoers.d/$USERNAME

CMD ["/bin/bash", "-c", "while sleep 1000; do :; done"]

FROM python
