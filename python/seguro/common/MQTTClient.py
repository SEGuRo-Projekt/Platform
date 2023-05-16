import paho.mqtt.client as mqtt
from queue import Queue


class MQTTClient:

    def __init__(self):
        self.client = self.__mqtt_create_client()
        self.messageQueue = Queue()

    # The callback function of connection
    def __on_connect(self, client, userdata, flags, rc):
        print(f"Connected with result code {rc}")

    # The callback function for received message
    def __on_message(self, client, userdata, msg):
        print(msg.topic+" "+str(msg.payload))
        self.messageQueue.put(msg)

    def __mqtt_create_client(self):
        client = mqtt.Client()
        client.on_connect = self.__on_connect
        client.on_message = self.__on_message
        return client

    def connect(self, broker, port, username=None, password=None, keepalive=60):
        if username is not None or password is not None:
            self.client.username_pw_set(username, password)

        self.client.connect(broker, port, keepalive)

    def subscribe(self, topic):
        self.client.subscribe(topic)

    def start_listening(self):
        self.client.loop_start()

    def stop_listening(self):
        self.client.loop_stop()

    def publish(self, topic, message):
        self.client.publish(topic, message)
