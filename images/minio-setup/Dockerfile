# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

FROM golang:1.20-alpine as builder

RUN  go install github.com/minio/mc@latest

FROM python:3.11

COPY --from=builder /go/bin/mc /usr/bin/mc

RUN pip install --no-cache-dir \
    minio==7.1.14

RUN apt-get update && \
    apt-get install --yes --no-install-recommends \
        openssh-client=1:8.4p1-5+deb11u1 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
