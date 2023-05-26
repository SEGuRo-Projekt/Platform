"""
SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
SPDX-License-Identifier: Apache-2.0
"""


from seguro.platform.config import S3_HOST


def test_default_config():
    assert S3_HOST == "minio"
