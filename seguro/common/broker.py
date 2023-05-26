"""
SPDX-FileCopyrightText: 2023 Felix Wege, EONERC-ACS, RWTH Aachen University
SPDX-License-Identifier: Apache-2.0
"""

from queue import Queue
import os

import logging
from logging.handlers import RotatingFileHandler

import paho.mqtt.client as mqtt
from seguro.common.config import (
    MQTT_HOST,
    MQTT_PASSWORD,
    MQTT_PORT,
    MQTT_USERNAME,
    LOG_LEVEL,
)


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
        log_level=LOG_LEVEL,
    ):
        """Broker Constructor

        Create a paho.mqtt.client object and initialize the message queue.

        Arguments:
            uid -- Unique id/name of the client (default empty string "")
        """
        self.client = client = mqtt.Client(client_id=uid)

        client.on_connect = self.__on_connect
        client.on_message = self.__on_message

        if username is not None or password is not None:
            self.client.username_pw_set(username, password)

        self.client.connect(host, port, keepalive)

        self.message_queue = Queue()

        self.logger = logger = logging.getLogger("brokerClient_logger")
        logger.setLevel(log_level)

        handler = RotatingFileHandler(
            os.path.join(
                os.path.dirname(__file__),
                "../../log/brokerclient/brokerclient.log",
            ),
            maxBytes=20000,
            backupCount=5,
        )
        logger.addHandler(handler)

        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)

    def __on_connect(self, client, userdata, flags, rc):
        self.logger.info("Connected with result code %i", rc)

    def __on_message(self, client, userdata, msg):
        self.logger.debug("Receive msg: %s - %s", msg.topic, str(msg.payload))
        self.message_queue.put(msg)

    def subscribe(self, topic):
        """Subscribe client to given topic."""
        self.client.subscribe(topic)
        self.logger.info("Subscribed to %s", topic)

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
