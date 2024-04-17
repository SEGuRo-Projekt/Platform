# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-FileCopyrightText: 2023 Felix Wege, EONERC-ACS, RWTH Aachen University
# SPDX-License-Identifier: Apache-2.0

import pytest
from seguro.common import config


@pytest.mark.config
def test_default_config():
    assert config.S3_BUCKET == "seguro"
