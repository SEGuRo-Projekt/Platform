# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

FROM python:3.11 AS python

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


FROM python
