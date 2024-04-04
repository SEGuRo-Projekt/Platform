"""
SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
SPDX-License-Identifier: Apache-2.0
"""

import sys
import signal
import logging
import docker
import seguro.common.store as store

from seguro.commands.scheduler.scheduler import Scheduler


def main() -> int:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s.%(msecs)03d %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    store_client = store.Client()
    docker_client = docker.from_env()

    scheduler = Scheduler(docker_client, store_client)

    def signal_handler(signum, frame):
        logging.info("Stopping scheduler")
        scheduler.stop()

    signal.signal(signal.SIGINT, signal_handler)

    scheduler.run()

    logging.info("Goodbye")

    return 0


if __name__ == "__main__":
    sys.exit(main())
