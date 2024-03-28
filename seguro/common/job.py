# SPDX-FileCopyrightText: 2023 Felix Wege, EONERC-ACS, RWTH Aachen University
# SPDX-License-Identifier: Apache-2.0

import os
import json
from types import SimpleNamespace


def _get_job_info() -> dict:
    info_raw = os.environ.get("SEGURO_JOB_INFO")
    if info_raw is None:
        raise Exception("Missing job details")

    return json.loads(
        info_raw, object_hook=lambda item: SimpleNamespace(**item)
    )


info = _get_job_info()
