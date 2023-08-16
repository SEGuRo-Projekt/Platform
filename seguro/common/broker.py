"""
SPDX-FileCopyrightText: 2023 Felix Wege, EONERC-ACS, RWTH Aachen University
SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
SPDX-License-Identifier: Apache-2.0
"""

import uuid
import logging

from typing import Optional, Callable

import paho.mqtt.client as mqtt

from seguro.common.config import (
    MQTT_HOST,
    MQTT_PASSWORD,
    MQTT_PORT,
    MQTT_USERNAME,
)

Message = mqtt.MQTTMessage


class BrokerClient:
    """Helper class for MQTT interaction with the SEGuRo platform.

    This class provides an abstraction layer for MQTT based communication
    between the SEGuRo platform and the MQTT broker.
    """

    def __init__(
        self,
        uid="",
        host=MQTT_HOST,
        port=MQTT_PORT,
        username=MQTT_USERNAME,
        password=MQTT_PASSWORD,
        keepalive=60,
    ):
        """Broker Constructor

        Create a paho.mqtt.client object and initialize the message queue.

        Arguments:
            uid -- Unique id/name of the client
        """
        if not uid:
            # Create uid based onMAC address and time component
            uid = str(uuid.uuid1())
        else:
            uid = uid

        self.logger = logging.getLogger(__name__)
        self.client = mqtt.Client(client_id=uid)

        if username is not None or password is not None:
            self.client.username_pw_set(username, password)

        self.client.connect(host, port, keepalive)

        self.start_listening()

    def __del__(self):
        self.stop_listening()

    def subscribe(
        self,
        topic,
        cb: Optional[Callable["BrokerClient", mqtt.MQTTMessage]] = None,
    ):
        """Subscribe client to given topic and registering callback (optional).

        Arguments:
            topic -- topic that is subscribed

        Optional:
            callback -- callback func that is called on message reception.
                        If no callback set, the default __on_message is called
        """
        self.client.subscribe(topic)

        if cb:

            def callback(_client, _ctx, msg):
                cb(self, msg)

            self.client.message_callback_add(topic, callback)
            self.logger.info(
                "Subscribed to %s with callback-func %s", topic, cb
            )

    def start_listening(self):
        """Start async listening on subscribed topics."""
        self.client.loop_start()

    def stop_listening(self):
        """Stop async listening on subscribed topics."""
        self.client.loop_stop()

    def publish(self, topic, message):
        """Publish message to given topic."""
        self.logger.debug("Send msg: %s - %s", topic, message)
        self.client.publish(topic, message)
