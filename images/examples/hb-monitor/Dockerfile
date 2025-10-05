# SPDX-FileCopyrightText: 2025 Jones Chakkalakkal, RWTH Aachen University
# SPDX-License-Identifier: Apache-2.0

FROM seguro/platform
ENV MQTT_HOST=mosquitto
RUN mkdir /src
WORKDIR /src
COPY . /src
RUN pip install --no-cache-dir .
CMD ["hb-mon-ui"]
