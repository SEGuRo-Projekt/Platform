"""
SPDX-FileCopyrightText: 2023 Felix Wege, EONERC-ACS, RWTH Aachen University
SPDX-License-Identifier: Apache-2.0
"""

import logging
from logging.handlers import RotatingFileHandler


def init_logger(log_level, logfile, max_bytes=20000, backup_count=5):
    """Return logger object.

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
    streamhandler = logging.StreamHandler()
    streamformatter = logging.Formatter("\033[31;1mERROR:\033[0m %(message)s")
    streamhandler.setFormatter(streamformatter)
    streamhandler.setLevel(logging.ERROR)

    logger.addHandler(streamhandler)

    return logger
