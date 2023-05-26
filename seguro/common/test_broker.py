"""
SPDX-FileCopyrightText: 2023 Felix Wege, EONERC-ACS, RWTH Aachen University
SPDX-License-Identifier: Apache-2.0
"""

import time

from seguro.common.broker import BrokerClient


def test_broker():
    broker = BrokerClient()

    # Subscribe to topic "mytopic" and start listening in another thread
    broker.subscribe("mytopic")
    broker.start_listening()

    # Publish messages to topic "mytopic"
    broker.publish("mytopic", "Hello MQTT!")
    broker.publish("mytopic", "Aaaand another one...")

    #  Make sure messages are completely sent...
    time.sleep(1)

    # Read messages are stored in a messageQueue of the client
    assert broker.message_queue.empty() is False

    # Read messages directly from client message queue
    while not broker.message_queue.empty():
        msg = broker.message_queue.get()
        print(f"{msg.topic} : {msg.payload}")

    # Note that queue.get() removes messages from queue
    assert broker.message_queue.empty() is True

    # Stop listening for new messages
    broker.stop_listening()

    # Note that messsages send after listening has stopped,
    # are not put into message queue
    broker.publish("mytopic", "Hello again!")
    assert broker.message_queue.empty() is True
