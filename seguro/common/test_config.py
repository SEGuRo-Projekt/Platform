"""
SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
SPDX-License-Identifier: Apache-2.0
"""


from seguro.common.config import S3_BUCKET


def test_default_config():
    assert S3_BUCKET == "seguro"
