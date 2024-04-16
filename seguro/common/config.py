# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import os
import logging

import environ

env = environ.Env()

# Take environment variables from .env file
environ.Env.read_env(os.path.join(os.getcwd(), ".env"))

DEBUG = env.bool("DEBUG", False)

# Logging
LOG_LEVEL = logging.DEBUG
MAX_BYTES = 20000
BACKUP_COUNT = 5

# Authentication
TLS_CACERT = env.str("TLS_CACERT", "/certs/ca.crt")
TLS_CERT = env.str("TLS_CERT", "/certs/client-admin.crt")
TLS_KEY = env.str("TLS_KEY", "/keys/client-admin.key")

# Object storage
S3_HOST = env.str("S3_HOST", "minio")
S3_PORT = env.int("S3_PORT", 9001)
S3_REGION = env.str("S3_REGION", "us-east-1")
S3_BUCKET = env.str("S3_BUCKET", "seguro")

# Message broker
MQTT_HOST = env.str("MQTT_HOST", "mosquitto")
MQTT_PORT = env.int("MQTT_PORT", 1883)
