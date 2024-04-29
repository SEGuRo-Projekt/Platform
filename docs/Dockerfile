# SPDX-FileCopyrightText: 2023-2024 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

FROM python:3.11-bookworm AS builder

RUN pip install --no-cache-dir poetry==1.7.1

RUN mkdir /src
WORKDIR /src

RUN apt-get -y update && \
    apt-get -y install --no-install-recommends \
    libgraphviz-dev \
    pkg-config \
    graphviz

COPY pyproject.toml poetry.lock /src/

RUN poetry install --with=docs

COPY seguro /src/seguro
COPY docs /src/docs
COPY .env.example /src

RUN poetry run sphinx-build -T -b html docs /build

FROM nginx:1.25.4

COPY --from=builder /build /usr/share/nginx/html
