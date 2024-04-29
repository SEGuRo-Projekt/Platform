# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import sys
import os
import json

from seguro.commands.scheduler import model


def _get_job_info() -> model.JobInfo | None:
    info_raw = os.environ.get("SEGURO_JOB_INFO")
    if info_raw is None or "sphinx" in sys.modules:
        return None

    return model.JobInfo(**json.loads(info_raw))


info: model.JobInfo | None = _get_job_info()
