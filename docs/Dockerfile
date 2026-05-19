# SPDX-FileCopyrightText: 2023-2026 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

FROM python:3.11-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.15 /uv /usr/local/bin/uv

RUN mkdir /src
WORKDIR /src

RUN apt-get update && \
    apt-get install --yes --no-install-recommends \
    graphviz \
    libgraphviz-dev \
    pkg-config && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock /src/

RUN uv sync --group docs

COPY seguro /src/seguro
COPY docs /src/docs
COPY .env.example /src

RUN uv run sphinx-build -T -b html docs /build

FROM nginx:1.25.4

COPY --from=builder /build /usr/share/nginx/html
