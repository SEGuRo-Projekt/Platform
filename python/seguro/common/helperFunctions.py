from minio import Minio
import os
import io

########################################################################
## S3 Storage Functions
########################################################################
def connect_to_storage(SERVER, PORT, ACCESS_KEY, SECRET_KEY):
    client = Minio(endpoint=SERVER+":"+PORT,
                   access_key=ACCESS_KEY,
                   secret_key=SECRET_KEY,
                   secure=False)
    return client

def get_file(client, filename, file, bucket="seguro"):
    if not client.bucket_exists(bucket):
        print(f"Error: Bucket \"{bucket}\" does not exist...")
        return

    client.fget_object(
        bucket, file, filename
    )


def put_file(client, filename, file, bucket="seguro"):
    if not client.bucket_exists(bucket):
        print(f"Error: Bucket \"{bucket}\" does not exist...")
        return

    client.fput_object(
        bucket, filename, file
    )

def write_to_file(client, filename, message, bucket="seguro"):
    if not client.bucket_exists(bucket):
        print(f"Error: Bucket \"{bucket}\" does not exist...")
        return

    client.put_object(
        bucket, filename, io.BytesIO(b"%a" % message), len(message)
    )

def file_changed(client, filename, last_modified, bucket="seguro"):
    if not client.bucket_exists(bucket):
        print(f"Error: Bucket \"{bucket}\" does not exist...")
        return

    stats = client.stat_object(
        bucket, filename
    )

    if last_modified != stats._last_modified:
        return True
    else:
        return False

########################################################################
## MQTT Functions
########################################################################
import paho.mqtt.client as mqtt

# The callback function of connection
def __on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")

# The callback function for received message
def __on_message(client, userdata, msg):
    global messageQueue
    # if messageQueue not in globals():
    #     print(f"Error: messageQueue does not exist...")
    #     return
    # else:
    print(msg.topic+" "+str(msg.payload))
    messageQueue.put(msg)

    # return msg


def mqtt_create_client():
    client = mqtt.Client()
    client.on_connect = __on_connect
    client.on_message = __on_message
    return client

def mqtt_connect(client, broker, port, username=None, password=None, keepalive=60):
    if username is not None or password is not None:
        client.username_pw_set(username, password)

    client.connect(broker, port, keepalive)

def mqtt_subscribe(client, topic):
    client.subscribe(topic)

def mqtt_start_listening(client):
    client.loop_start()

def mqtt_stop_listening(client):
    client.loop_stop()

def mqtt_publish(client, topic, message):
    client.publish(topic, message)


if __name__ == "__main__":
    client = connect_to_storage("localhost", "9000", os.environ["S3_ACCESS_KEY"], os.environ["S3_SECRET_KEY"])


    buckets = client.list_buckets()
    for bucket in buckets:
        print(bucket.name, bucket.creation_date)

    mqtt = mqtt_create_client()
    mqtt_connect(mqtt, "localhost", 1884, "felix")
    mqtt_subscribe(mqtt, "topic")


    # put_file(client, "MyFile", "./helperFunctions.py")
    # get_file(client, "MyFile.py", "MyFile", bucket="auto")
    # stats1 = file_changed(client, "log.txt", bucket="testbucket")
    # write_to_file(client, "log.txt", "Mys log message...\n", bucket="testbucket")
    # client.make_bucket("my-bucket")
