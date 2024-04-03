"""
SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
SPDX-License-Identifier: Apache-2.0
"""

import sys
import time
import random
import logging

from seguro.common import broker


def main() -> int:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s.%(msecs)03d %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    b = broker.Client("demo-data")

    value = 0.0

    while True:
        b.publish("measurements/ms1/value", value)
        value += 0.1 * random.uniform(-1, 1)
        time.sleep(0.1)


if __name__ == "__main__":
    sys.exit(main())
