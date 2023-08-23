"""
SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
SPDX-License-Identifier: Apache-2.0
"""

import logging
import time

from seguro.common.broker import BrokerClient, Message


def new_value(broker: BrokerClient, msg: Message):
    value = float(msg.payload)
    logging.info(f"Got value {value:.2}")


def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s.%(msecs)03d %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    broker = BrokerClient("recorder")

    broker.subscribe("measurements/ms1/value", new_value)

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
