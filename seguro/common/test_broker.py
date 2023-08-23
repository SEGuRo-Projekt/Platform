"""
SPDX-FileCopyrightText: 2023 Felix Wege, EONERC-ACS, RWTH Aachen University
SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
SPDX-License-Identifier: Apache-2.0
"""

import time
import pytest

from seguro.common.broker import BrokerClient

# Used to store callback messages
messages = []


def callback(client, msg):
    messages.append(msg)


@pytest.mark.broker
def test_broker():
    broker = BrokerClient("pytest-broker")

    # Subscribe to topic "mytopic" and start listening in another thread
    broker.subscribe("mytopic", callback)

    # Publish messages to topic "mytopic"
    broker.publish("mytopic", "Hello MQTT!")

    #  Make sure messages are completely sent...
    time.sleep(1)

    assert len(messages) == 1
    assert messages[0].topic == "mytopic"
    assert messages[0].payload == b"Hello MQTT!"
