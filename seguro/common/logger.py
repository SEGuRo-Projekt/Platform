# SPDX-FileCopyrightText: 2023 Felix Wege, EONERC-ACS, RWTH Aachen University
# SPDX-License-Identifier: Apache-2.0

import logging
from logging.handlers import RotatingFileHandler
from aws_logging_handlers.S3 import S3Handler
from minio.credentials import CertificateIdentityProvider

from seguro.common.config import (
    TLS_CACERT,
    TLS_CERT,
    TLS_KEY,
    S3_HOST,
    S3_PORT,
    S3_BUCKET,
)


def file_logger(log_level, logfile, max_bytes=20000, backup_count=5):
    """

    Args:
      log_level: Log level for logfiles
      logfile: Path to logfile
      max_bytes:  (Default value = 20000)
      backup_count:  (Default value = 5)

    Returns:


    """
    logger = logging.getLogger("file_logger")
    logger.setLevel(log_level)

    # Log specified log level to file
    filehandler = RotatingFileHandler(
        logfile,
        maxBytes=max_bytes,
        backupCount=backup_count,
    )
    fileformatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )
    filehandler.setFormatter(fileformatter)
    filehandler.setLevel(log_level)
    logger.addHandler(filehandler)

    # Additionally log errors to stderr
    logger.addHandler(error_handler())

    return logger


def store_logger(log_level, logfile, bucket=S3_BUCKET):
    """Return logger object that logs into s3 storage.

    Args:
      log_level: Log level for logfiles
      logfile: Path to logfile
      bucket: Bucket name for logfiles (Default value = S3_BUCKET)

    Returns:


    """

    logger = logging.getLogger("store_logger")
    logger.setLevel(log_level)

    # Log specified log level to file
    store_endpoint = f"https://{S3_HOST}:{S3_PORT}"
    store_creds_provider = CertificateIdentityProvider(
        sts_endpoint=store_endpoint,
        ca_certs=TLS_CACERT,
        cert_file=TLS_CERT,
        key_file=TLS_KEY,
    )
    store_creds = store_creds_provider.retrieve()
    store_handler = S3Handler(
        f"logs/{logfile}",
        bucket=bucket,
        endpoint_url=store_endpoint,
        aws_access_key_id=store_creds.access_key,
        aws_secret_access_key=store_creds.secret_key,
        encryption_options={},
    )

    storeformatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )
    store_handler.setFormatter(storeformatter)
    store_handler.setLevel(log_level)
    logger.addHandler(store_handler)

    # Additionally log errors to stderr
    logger.addHandler(error_handler())

    return logger


def error_handler():
    """Return a streaming handler logging warnings and errors to stderr."""
    streamhandler = logging.StreamHandler()
    streamformatter = logging.Formatter(
        "\033[31;1m%(levelname)s:\033[0m %(message)s"
    )
    streamhandler.setFormatter(streamformatter)
    streamhandler.setLevel(logging.WARNING)

    return streamhandler
