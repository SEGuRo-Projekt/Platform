"""
SPDX-FileCopyrightText: 2023 Felix Wege, EONERC-ACS, RWTH Aachen University
SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
SPDX-License-Identifier: Apache-2.0
"""

import uuid
import logging

from typing import Callable, Iterable

import paho.mqtt.client as mqtt
from paho.mqtt.client import PayloadType, MQTTMessageInfo
from villas.node.sample import Sample, Timestamp  # noqa: F401
from villas.node.formats import Protobuf

from seguro.common.config import (
    MQTT_HOST,
    MQTT_PASSWORD,
    MQTT_PORT,
    MQTT_USERNAME,
)

Message = mqtt.MQTTMessage


class Client:
    """Helper class for MQTT interaction with the SEGuRo platform.

    This class provides an abstraction layer for MQTT based communication
    between the SEGuRo platform and the MQTT broker.

    Creates a paho.mqtt.client object and initialize the message queue.

    Args:
      uid: An identifier of the client
      host: The MQTT hostname or IP address. Defaults to localhost.
      port: The port number used for connecting to the MQTT broker.
            Defaults to 1883.
      username: The username for authentication of MQTT broker.
      password: The password for authentication of MQTT broker.
      keepalive: The keepalive interval in seconds.

    """

    def __init__(
        self,
        uid=None,
        host=MQTT_HOST,
        port=MQTT_PORT,
        username=MQTT_USERNAME,
        password=MQTT_PASSWORD,
        keepalive=60,
    ):
        # Create uid based onMAC address and time component
        if uid is None:
            uid = str(uuid.uuid1())
        else:
            uid += "/" + str(uuid.uuid1())

        self.logger = logging.getLogger(__name__)
        self.client = mqtt.Client(
            client_id=uid,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )

        if username is not None or password is not None:
            self.client.username_pw_set(username, password)

        self.client.connect(host, port, keepalive)

        self.start_listening()

    def __del__(self):
        self.stop_listening()

    def subscribe(
        self,
        topic,
        cb: Callable[["Client", mqtt.MQTTMessage], None],
    ):
        """Subscribe client to given topic and registering callback (optional).

        Args:
          topic: The topic that is subscribed
          callback: A callback func that is called on message reception

        """
        self.client.subscribe(topic)

        def callback(_client, _ctx, msg):
            cb(self, msg)

        self.client.message_callback_add(topic, callback)
        self.logger.debug("Subscribed to %s with callback-func %s", topic, cb)

    def start_listening(self):
        """Start async listening on subscribed topics."""
        self.client.loop_start()

    def stop_listening(self):
        """Stop async listening on subscribed topics."""
        self.client.loop_stop()

    def publish(self, topic: str, message: PayloadType) -> MQTTMessageInfo:
        """Publish message to given topic

        Args:
          topic:
          message:

        Returns:
            MQTTMessageInfo: The MQTT message information

        """
        self.logger.debug("Send msg: %s - %s", topic, message)

        return self.client.publish(topic, message)

    def subscribe_samples(
        self, topic: str, cb: Callable[["Client", str, list[Sample]], None]
    ):
        """Subscribe client to given topic and registering callback (optional).

        Args:
          topic: The topic that is subscribed
          cb: The callback func that is called for each received sample

        """

        def on_message(client: "Client", msg: mqtt.MQTTMessage):
            cb(client, msg.topic, Protobuf().loadb(msg.payload))

        self.subscribe(topic, on_message)

    def publish_samples(
        self, topic, samples: Iterable[Sample]
    ) -> MQTTMessageInfo:
        """Publish sample to given topic.

        Args:
          topic:
          samples:

        Returns:
            MQTTMessageInfo: The MQTT message information

        """

        return self.publish(topic, Protobuf().dumpb(samples))
