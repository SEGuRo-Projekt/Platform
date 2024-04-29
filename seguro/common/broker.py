# SPDX-FileCopyrightText: 2023 Felix Wege, EONERC-ACS, RWTH Aachen University
# SPDX-FileCopyrightText: 2023-2024 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import uuid
import logging

from typing import Callable, Iterable

import paho.mqtt.client as mqtt
from paho.mqtt.client import PayloadType, MQTTMessageInfo
from villas.node.sample import Sample, Timestamp  # noqa: F401
from villas.node.formats import Protobuf

from seguro.common import config

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
            Defaults to 8883.
      tls_cert: File containing the TLS client certificate for mutual TLS
                authentication.
      tls_key: File containing the TLS client key for mutual TLS
               authentication.
      tls_cacert: File containing the TLS certificate authority to validate
                  the servers certificate against.
      keepalive: The keepalive interval in seconds.

    """

    def __init__(
        self,
        uid=None,
        host: str = config.MQTT_HOST,
        port: int = config.MQTT_PORT,
        tls_cert: str = config.TLS_CERT,
        tls_key: str = config.TLS_KEY,
        tls_cacert: str = config.TLS_CACERT,
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
        self.client.tls_set(
            ca_certs=tls_cacert,
            certfile=tls_cert,
            keyfile=tls_key,
        )

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
            self.logger.debug("Recv msg: %s - %s", msg.topic, msg.payload)
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
