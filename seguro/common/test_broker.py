"""
SPDX-FileCopyrightText: 2023 Felix Wege, EONERC-ACS, RWTH Aachen University
SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
SPDX-License-Identifier: Apache-2.0
"""

import time
import pytest

from seguro.common.broker import Client, Sample, Timestamp


@pytest.mark.broker
def test_broker():
    broker = Client("pytest-broker")

    # Used to store callback messages
    messages = []

    def callback(client, msg):
        messages.append(msg)

    # Subscribe to topic "mytopic" and start listening in another thread
    broker.subscribe("mytopic", callback)

    # Publish messages to topic "mytopic"
    broker.publish("mytopic", "Hello MQTT!")

    #  Make sure messages are completely sent...
    time.sleep(1)

    assert len(messages) == 1
    assert messages[0].topic == "mytopic"
    assert messages[0].payload == b"Hello MQTT!"


@pytest.mark.broker
def test_broker_samples():
    broker = Client("pytest-broker")

    # Used to store callback messages
    smps_recv: list[Sample] = []

    def callback(client, samples: list[Sample]):
        smps_recv.extend(samples)

    # Subscribe to topic "mytopic" and start listening in another thread
    broker.subscribe_samples("mytopic", callback)

    smp1 = Sample(
        ts_origin=Timestamp(123456780),
        ts_received=Timestamp(123456781),
        sequence=4,
        new_frame=True,
        data=[1.0, 2.0, 3.0, True, 42, complex(-1, 2)],
    )

    smp2 = Sample(
        ts_origin=Timestamp(123456789),
        ts_received=Timestamp(123456790),
        sequence=5,
        new_frame=False,
        data=[1.0, 2.0, 3.0, False, 42, complex(1, -1)],
    )

    smps_send = [smp1, smp2]

    # Publish messages to topic "mytopic"
    broker.publish_samples("mytopic", smps_send)

    #  Make sure messages are completely sent...
    time.sleep(1)

    assert len(smps_recv) == 2
    assert smps_recv == smps_send
