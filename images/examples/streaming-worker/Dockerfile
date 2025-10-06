# SPDX-FileCopyrightText: 2023-2024 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

FROM python:3.11.8-bookworm

RUN mkdir /src
WORKDIR /src

COPY . /src
RUN pip install --no-cache-dir .

CMD ["streaming-worker"]
