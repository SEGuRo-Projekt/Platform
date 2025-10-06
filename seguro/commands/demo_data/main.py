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

from villas.node.formats import Protobuf, Sample, Timestamp

from seguro.common import broker, config

env = environ.Env()

# Authentication
TOPIC = env.str("TOPIC", "data/measurements/demo-data")
RATE = env.float("RATE", 10.0)
VALUES = env.int("VALUES", 6)
BLOCK_INTERVAL = env.str("BLOCK_INTERVAL", "1m")
SAMPLE_TYPE = env.str("SAMPLE_TYPE", "simple")


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
    parser.add_argument(
        "-s",
        "--sample-type",
        default=SAMPLE_TYPE,
        help="Type of sample data to generate",
        choices=["simple", "measurement"],
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s.%(msecs)03d %(levelname)s %(name)s %(message)s",
        datefmt="%H:%M:%S",
    )

    b = broker.Client("demo-data")
    pb = Protobuf()

    last_block = datetime.now()
    block_interval = timedelta(args.block_interval)

    while True:

        if args.sample_type == "simple":
            data = args.values * [0.0]
            for i, _ in enumerate(data):
                data[i] += 0.1 * random.uniform(-1, 1)
        elif args.sample_type == "measurement":
            # Add random values within realistic measurement boundaries
            data = [
                # Voltage: 227.0 - 235.0 V
                *[
                    complex(
                        random.uniform(227.0, 235.0), random.uniform(0.0, 11.5)
                    )
                    for _ in range(3)
                ],
                # Current: 0.0 - 1.15 A
                *[
                    complex(
                        random.uniform(22.7, 23.5), random.uniform(0.0, 1.5)
                    )
                    for _ in range(3)
                ],
                # Power: 0.95 - 1.0
                *[
                    complex(
                        random.uniform(5152.9, 5522.5),
                        random.uniform(0.0, 17.25),
                    )
                    for _ in range(3)
                ],
                # Frequency: 49.9 - 50.1 Hz
                random.uniform(49.9, 50.1),
            ]
        else:
            raise ValueError(
                f"Unknown type of sample data: {args.sample_type}"
            )

        smp = Sample(data=data)
        epoch_time = time.time_ns()
        smp.ts_origin = Timestamp(
            seconds=int(epoch_time // 1e9), nanoseconds=int(epoch_time % 1e9)
        )

        if datetime.now() - last_block > block_interval:
            smp.new_frame = True
            last_block = datetime.now()
            logging.info("Starting new block")
        logging.debug("Publishing sample: %s", smp)
        b.publish(args.topic, pb.dumpb([smp]))

        time.sleep(1.0 / args.rate)

    return 0


if __name__ == "__main__":
    sys.exit(main())
