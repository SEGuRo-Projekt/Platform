# SPDX-FileCopyrightText: 2023-2024 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import sys
import time
import random
import logging
import argparse
import environ
from pytimeparse import parse as timeparse
from datetime import datetime, timedelta

from villas.node.formats import Protobuf, Sample

from seguro.common import broker, config

env = environ.Env()

# Authentication
TOPIC = env.str("TOPIC", "data/measurements/mp1")
RATE = env.float("RATE", 10.0)
VALUES = env.int("VALUES", 6)
BLOCK_INTERVAL = env.str("BLOCK_INTERVAL", "1m")


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument("-t", "--topic", type=str, default=TOPIC)
    parser.add_argument(
        "-r",
        "--rate",
        type=float,
        default=RATE,
        help="Rate at which samples are emitted",
    )
    parser.add_argument(
        "-v",
        "--values",
        type=int,
        default=VALUES,
        help="Number of signals per sample",
    )
    parser.add_argument(
        "-b",
        "--block-interval",
        type=timeparse,
        default=BLOCK_INTERVAL,
        help="Interval of blocks",
    )
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

    b = broker.Client("demo-data")
    pb = Protobuf()

    data = args.values * [0.0]

    last_block = datetime.now()
    block_interval = timedelta(args.block_interval)

    while True:
        smp = Sample(data=data)

        if datetime.now() - last_block > block_interval:
            smp.new_frame = True
            last_block = datetime.now()
            logging.info("Starting new block")

        b.publish(args.topic, pb.dumpb([smp]))

        for i, _ in enumerate(data):
            data[i] += 0.1 * random.uniform(-1, 1)

        time.sleep(1.0 / args.rate)

    return 0


if __name__ == "__main__":
    sys.exit(main())
