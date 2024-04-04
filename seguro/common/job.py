# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import sys
import os
import json
from types import SimpleNamespace


def _get_job_info():
    info_raw = os.environ.get("SEGURO_JOB_INFO")
    if info_raw is None:
        if "sphinx" in sys.modules:
            return None

        raise Exception("Missing job details")

    return json.loads(
        info_raw, object_hook=lambda item: SimpleNamespace(**item)
    )


info = _get_job_info()
