"""
SPDX-FileCopyrightText: 2023 Felix Wege, EONERC-ACS, RWTH Aachen University
SPDX-License-Identifier: Apache-2.0
"""

import seguro.common.logger
import logging
import os


def test_file_logger(capsys):

    filepath = os.path.join(
        os.path.dirname(__file__),
        "../../log/test_logger.log",
    )

    # Cleanup before test
    if os.path.isfile(filepath):
        os.remove(filepath)

    file_logger = seguro.common.logger.file_logger(logging.DEBUG, filepath)
    file_logger.error("Test-Error")

    assert os.path.isfile(filepath)
    with open(filepath) as file:
        log_msg = file.readline()
        assert "Test-Error" in log_msg

    captured = capsys.readouterr()
    assert captured.err == "\033[31;1mERROR:\033[0m Test-Error\n"

    # Cleanup after test
    if os.path.isfile(filepath):
        os.remove(filepath)
