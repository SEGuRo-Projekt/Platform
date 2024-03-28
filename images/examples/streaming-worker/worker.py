# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import sys
import time

from seguro.common import broker
from villas.node.sample import Sample


def new_samples(client: broker.Client, topic: str, samples: list[Sample]):
    for sample in samples:
        print(topic, sample)

        sample.data[0] *= 2
        sample.data[1] += 10

    client.publish_samples("data/scaled/ms1/mp1", samples)


def main() -> int:
    client = broker.Client("example-worker")

    client.subscribe_samples("data/ms1/mp1", new_samples)

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break

    return 0


if __name__ == "__main__":
    sys.exit(main())
