# SPDX-FileCopyrightText: 2023-2024 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import sys
import logging
import argparse

from seguro.common import store, config, job
from seguro.commands.scheduler.model import StoreTriggerType


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-l",
        "--log-level",
        default="debug" if config.DEBUG else "info",
        help="Logging level",
        choices=["debug", "info", "warn", "error", "critical"],
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s.%(msecs)03d %(levelname)s %(name)s %(message)s",
        datefmt="%H:%M:%S",
    )

    if (
        job.info is None
        or job.info.trigger is None
        or job.info.trigger.type != StoreTriggerType.CREATED
        or job.info.trigger.object is None
    ):
        logging.error("Invalid trigger")
        return -1

    s = store.Client()

    frame = s.get_frame(job.info.trigger.object)
    frame *= 2

    object_scaled = job.info.trigger.object.replace(
        "measurements", "measurements_processed"
    )

    s.put_frame(object_scaled, frame)

    return 0


if __name__ == "__main__":
    sys.exit(main())
