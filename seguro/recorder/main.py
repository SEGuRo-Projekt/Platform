"""
SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
SPDX-License-Identifier: Apache-2.0
"""

import argparse
import logging
import time
from typing import Iterable
import functools as ft

from seguro.common import store, broker
from seguro.common.broker import Sample
from seguro.recorder.recorder import Recorder

recorders: dict[str, Recorder] = {}


def on_samples(
    s: store.Client, _: broker.Client, topic: str, samples: Iterable[Sample]
):
    try:
        recorder = recorders[topic]
    except KeyError:
        recorder = Recorder(s, topic)
        recorders[topic] = recorder

    recorder.record_samples(samples)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("-p", "--prefix", type=str, default="data")
    parser.add_argument(
        "-l",
        "--log-level",
        default="info",
        help="Logging level",
        choices=["debug", "info", "warn", "error", "critical"],
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s.%(msecs)03d %(levelname)s %(name)s %(message)s",
        datefmt="%H:%M:%S",
    )

    b = broker.Client("recorder")
    s = store.Client()

    topic = f"{args.prefix}/#"

    b.subscribe_samples(topic, ft.partial(on_samples, s))

    logging.info("Subscribed to topic: %s", topic)

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
