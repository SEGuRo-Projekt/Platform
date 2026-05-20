# SPDX-FileCopyrightText: 2023-2026 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

FROM python:3.13.12-bookworm

RUN mkdir /src
WORKDIR /src

COPY . /src
RUN pip install --no-cache-dir .

CMD ["job-worker"]
