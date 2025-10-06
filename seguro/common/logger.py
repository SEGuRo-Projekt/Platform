# SPDX-FileCopyrightText: 2023 Felix Wege, EONERC-ACS, RWTH Aachen University
# SPDX-License-Identifier: Apache-2.0

import logging
from logging.handlers import RotatingFileHandler
from aws_logging_handlers.S3 import S3Handler
from minio.credentials import CertificateIdentityProvider

from seguro.common import config


def file_logger(
    log_level: int | str,
    log_file: str,
    max_bytes: int = 20000,
    backup_count: int = 5,
) -> logging.Logger:
    """

    Args:
      log_level: Log level for log files
      logfile: Path to logfile
      max_bytes: (Default value = 20000)
      backup_count: (Default value = 5)

    Returns:
      A logging.Logger instance configured for logging into the specified file.

    """
    logger = logging.getLogger("file_logger")
    logger.setLevel(log_level)

    # Log specified log level to file
    filehandler = RotatingFileHandler(
        log_file,
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


def store_logger(
    log_level: int | str,
    log_file: str,
    store_bucket: str = config.S3_BUCKET,
    store_host: str = config.S3_HOST,
    store_port: str = config.S3_PORT,
    tls_cert: str = config.TLS_CERT,
    tls_key: str = config.TLS_KEY,
    tls_cacert: str = config.TLS_CACERT,
) -> logging.Logger:
    """Return logger object that logs into s3 storage.

    Args:
      log_level: Log level for log files
      logfile: Path to logfile
      bucket: Bucket name for log files (Default value = S3_BUCKET)

    Returns:
      A logging.Logger instance with
    """

    logger = logging.getLogger("store_logger")
    logger.setLevel(log_level)

    # Log specified log level to file
    store_endpoint = f"https://{store_host}:{store_port}"
    store_creds_provider = CertificateIdentityProvider(
        sts_endpoint=store_endpoint,
        ca_certs=tls_cacert,
        cert_file=tls_cert,
        key_file=tls_key,
    )
    store_creds = store_creds_provider.retrieve()
    store_handler = S3Handler(
        f"logs/{log_file}",
        bucket=store_bucket,
        endpoint_url=store_endpoint,
        aws_access_key_id=store_creds.access_key,
        aws_secret_access_key=store_creds.secret_key,
        aws_session_token=store_creds.session_token,
        verify=config.TLS_CACERT,
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
