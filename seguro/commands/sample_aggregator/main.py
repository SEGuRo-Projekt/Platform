# SPDX-FileCopyrightText: 2025 Felix Wege, EONERC-ACS, RWTH Aachen University
# SPDX-License-Identifier: Apache-2.0

import argparse
from functools import partial
import logging
import time

import environ

from villas.node.formats import Sample

from seguro.common import broker, config


env = environ.Env()
TOPIC = env.str("TOPIC", "data/measurements/+/+/+")
CONNECTOR_ID = env.str("CONNECTOR_ID", "sample-aggregator")


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

    def callback(
        b: broker.Client,
        topic: str,
        samples: list[Sample],
    ):
        """Callback which gets called for each received MQTT message.

        Args:
            client: The broker client
            msg: The MQTT message

        """
        logging.debug(
            "%s, %s - %s - %s%s",
            samples[-1].ts_origin.seconds,
            samples[-1].ts_origin.nanoseconds,
            topic,
            samples[-1].data,
            samples[-1],
        )

        sample_index = 1
        sample_start = 3  # First three elements are always the voltages
        sample_end = len(samples[-1].data) - 1
        curr_end = sample_start + 12

        while curr_end <= sample_end:
            # Note: This currently does not send incomplete samples.
            # I.e., at least 3 Currents and 3 Power values have to be present.
            sample_range = list(range(sample_start, curr_end))

            samples[-1].data[4] += samples[-1].data[sample_range[0]]
            samples[-1].data[5] += samples[-1].data[sample_range[1]]
            samples[-1].data[6] += samples[-1].data[sample_range[2]]

            samples[-1].data[7] += samples[-1].data[sample_range[3]]
            samples[-1].data[8] += samples[-1].data[sample_range[4]]
            samples[-1].data[9] += samples[-1].data[sample_range[5]]

            sample_start = curr_end
            curr_end += 6
            sample_index += 1

        frequency = samples[-1].data[-1]
        samples[-1].data = samples[-1].data[:10]  # Drop non aggregated values
        samples[-1].data.append(frequency)  # Add frequency

        logging.debug("Aggregated sample data: %s", samples[-1].data)

        b.publish_samples(topic + "/aggregated", [samples[-1]])

    b = broker.Client(CONNECTOR_ID)

    for topic in TOPIC.split(","):
        b.subscribe_samples(topic, partial(callback))

    logging.info("Subscribed to %s", TOPIC)

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break

    return 0


if __name__ == "__main__":
    main()
