# SPDX-FileCopyrightText: 2023-2026 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import os
import logging
from pathlib import Path

import environ

env = environ.Env()

# Take environment variables from .env file
environ.Env.read_env(os.path.join(os.getcwd(), ".env"))

DEBUG = env.bool("DEBUG", False)

# Logging
LOG_LEVEL = logging.DEBUG
MAX_BYTES = 20000
BACKUP_COUNT = 5

DOMAIN = env.str("DOMAIN", "localhost")

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_from_project_root(p: str) -> str:
    path = Path(p).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return str(path.resolve())


# Authentication
TLS_CACERT = env.str("TLS_CACERT", resolve_from_project_root("keys/ca.crt"))
TLS_CERT = env.str("TLS_CERT", resolve_from_project_root("keys/clients/admin.crt"))
TLS_KEY = env.str("TLS_KEY", resolve_from_project_root("keys/clients/admin.key"))

# Object storage
S3_HOST = env.str("S3_HOST", "localhost")
S3_PORT = env.int("S3_PORT", 9000)
S3_REGION = env.str("S3_REGION", "minio")
S3_BUCKET = env.str("S3_BUCKET", "seguro")

# Message broker
MQTT_HOST = env.str("MQTT_HOST", "localhost")
MQTT_PORT = env.int("MQTT_PORT", 8883)
