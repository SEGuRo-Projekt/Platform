# SPDX-FileCopyrightText: 2023 Felix Wege, EONERC-ACS, RWTH Aachen University
# SPDX-License-Identifier: Apache-2.0

import logging
from logging.handlers import RotatingFileHandler
from aws_logging_handlers.S3 import S3Handler

from seguro.common.config import (
    S3_ACCESS_KEY,
    S3_HOST,
    S3_PORT,
    S3_SECRET_KEY,
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
    storehandler = S3Handler(
        f"logs/{logfile}",
        bucket=bucket,
        endpoint_url=f"http://{S3_HOST}:{S3_PORT}",
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        encryption_options={},
    )

    storeformatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )
    storehandler.setFormatter(storeformatter)
    storehandler.setLevel(log_level)
    logger.addHandler(storehandler)

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
