# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

FROM python:3.11 AS builder

RUN pip install --no-cache-dir poetry==1.7.1

RUN mkdir /src
WORKDIR /src

COPY pyproject.toml poetry.lock /src/

RUN poetry install

COPY seguro /src/seguro
COPY docs /src/docs

RUN poetry install --with=docs
RUN poetry run sphinx-build -b html docs /build

FROM nginx:1.25.4

COPY --from=builder /build /usr/share/nginx/html
