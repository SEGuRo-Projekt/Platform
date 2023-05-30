"""
SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
SPDX-License-Identifier: Apache-2.0
"""

import os

import environ

env = environ.Env()

# Take environment variables from .env file
environ.Env.read_env(os.path.join(os.getcwd(), ".env"))

DEBUG = env.bool("DEBUG", False)

# Object storage
S3_HOST = env.str("S3_HOST", "minio")
S3_PORT = env.int("S3_PORT", 9001)
S3_ACCESS_KEY = env.str("S3_ACCESS_KEY", None)
S3_SECRET_KEY = env.str("S3_SECRET_KEY", None)
S3_SECURE = env.bool("S3_SECURE", False)
S3_REGION = env.str("S3_REGION", "us-east-1")
S3_BUCKET = env.str("S3_BUCKET", "seguro")

# Message broker
MQTT_HOST = env.str("MQTT_HOST", "mosquitto")
MQTT_PORT = env.int("MQTT_PORT", 1883)
MQTT_USERNAME = env.str("MQTT_USERNAME", None)
MQTT_PASSWORD = env.str("MQTT_PASSWORD", None)
