"""
SPDX-FileCopyrightText: 2023 Steffen Vogel <steffen.vogel@opal-rt.com>, OPAL-RT Germany GmbH
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
S3_REGION = env.str("S3_REGION", "us-east-1")
S3_USER = env.str("S3_USER", None)
S3_PASSWORD = env.str("S3_PASSWORD", None)

# Message broker
MQTT_HOST = env.str("MQTT_HOST", "mosquitto")
MQTT_PORT = env.int("MQTT_PORT", 1883)
MQTT_USER = env.str("MQTT_USER", None)
MQTT_PASSWORD = env.str("MQTT_PASSWORD", None)
