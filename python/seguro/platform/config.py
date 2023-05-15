"""
SPDX-FileCopyrightText: 2023 SEGuRo Project Consortium
SPDX-License-Identifier: Apache-2.0
"""

import environ
import os

env = environ.Env(
    DEBUG=(bool, False),
    S3_PORT=(int, 9001),
    MQTT_PORT=(int, 1883)
)

# Take environment variables from .env file
environ.Env.read_env(os.path.join(os.getcwd(), '.env'))

DEBUG = env('DEBUG')

# Object storage
S3_HOST = env('S3_HOST')
S3_PORT = env('S3_PORT')
S3_REGION = env('S3_REGION')
S3_USER = env('S3_USER')
S3_PASSWORD = env('S3_PASSWORD')

# Message broker
MQTT_HOST = env('MQTT_HOST')
MQTT_PORT = env('MQTT_PORT')
MQTT_USER = env('MQTT_USER')
MQTT_PASSWORD = env('MQTT_PASSWORD')
