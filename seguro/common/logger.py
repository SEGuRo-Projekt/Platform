"""
SPDX-FileCopyrightText: 2023 Felix Wege, EONERC-ACS, RWTH Aachen University
SPDX-License-Identifier: Apache-2.0
"""

import logging
from logging.handlers import RotatingFileHandler
from aws_logging_handlers.S3 import S3Handler


def file_logger(log_level, logfile, max_bytes=20000, backup_count=5):
    """Return logger object that logs into local files.

    Arguments:
        log_level   -- Log level for logfiles
        logfile     -- Path to logfile
    """
    logger = logging.getLogger("brokerClient_logger")
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


def store_logger(log_level, logfile, bucket):
    """Return logger object that logs into s3 storage.

    Arguments:
        log_level   -- Log level for logfiles
        logfile     -- Path to logfile
        bucket      -- Bucket name for logfiles
    """

    logger = logging.getLogger("brokerClient_logger")
    logger.setLevel(log_level)

    # Log specified log level to file
    storehandler = S3Handler(
        logfile,
        bucket=bucket,
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
    """Return a streaming handler logging errors to stderr."""
    streamhandler = logging.StreamHandler()
    streamformatter = logging.Formatter("\033[31;1mERROR:\033[0m %(message)s")
    streamhandler.setFormatter(streamformatter)
    streamhandler.setLevel(logging.ERROR)

    return streamhandler
