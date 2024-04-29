# SPDX-FileCopyrightText: 2023-2024 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import sys
import time
import argparse
import environ
import logging
from functools import partial

from seguro.common import broker, config
from villas.node.sample import Sample

env = environ.Env()

# Authentication
TOPIC = env.str("TOPIC", "data/measurements/mp1")
TOPIC_PROCESSED = env.str(
    "TOPIC", "data/measurements/processed_by_streaming_worker/mp1"
)
RATE = env.float("RATE", 10.0)
VALUES = env.int("VALUES", 6)
BLOCK_INTERVAL = env.str("BLOCK_INTERVAL", "1m")


def new_samples(args, b: broker.Client, topic: str, samples: list[Sample]):
    for sample in samples:
        print(topic, sample)

        for i, _ in enumerate(sample.data):
            sample.data[i] *= i

    b.publish_samples(args.topic_processed, samples)


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument("-t", "--topic", type=str, default=TOPIC)
    parser.add_argument(
        "-s", "--topic-processed", type=str, default=TOPIC_PROCESSED
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

    b = broker.Client("example-streaming-worker")

    b.subscribe_samples(args.topic, partial(new_samples, args))

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break

    return 0


if __name__ == "__main__":
    sys.exit(main())
