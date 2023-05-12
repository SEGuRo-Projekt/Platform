#########################################################################
### MQTT Example
#########################################################################

from MQTTclient import MQTTclient
import time

# Create MQTTclient and connect to mosquitto broker
mqtt = MQTTclient()
mqtt.connect("localhost", 1884)

# Subscribe to topic "mytopic" and start listening for messages in another thread
mqtt.subscribe("mytopic")
mqtt.start_listening()

# Publish messages to topic "mytopic"
mqtt.publish("mytopic", "Hello MQTT!")
mqtt.publish("mytopic", "Aaaand another one...")

#  Make sure messages are completely sent...
time.sleep(1)

# Read messages are stored in a messageQueue of the client
assert mqtt.messageQueue.empty() == False

# Read messages directly from client message queue
while not mqtt.messageQueue.empty():
    msg = mqtt.messageQueue.get()
    print(f"{msg.topic} : {msg.payload}")

# Note that queue.get() removes messages from queue
assert mqtt.messageQueue.empty() == True

# Stop listening for new messages
mqtt.stop_listening()

# Note that messsages send after listening has stopped, are not put into message queue
mqtt.publish("mytopic", "Hello again!")
assert mqtt.messageQueue.empty() == True


#########################################################################
### S3Storage Example
#########################################################################

from S3Storage import S3Storage
import os

storage = S3Storage("localhost", 9000 , os.environ["S3_ACCESS_KEY"], os.environ["S3_SECRET_KEY"])

# Create new file and fill with content
if not os.path.isfile("myfile.txt"):
    f = open("myfile.txt", "xw")

f = open("myfile.txt", "w")
f.write("Hello S3Storage!")
f.close()

# Put file into storage
storage.put_file("myStorageFile.txt", "myfile.txt", bucket="testbucket")

# Check if file has changed...
# Note: As the storage client cannot know if the file changed on the first call
#       file_changed() will always return True on first call
assert storage.file_changed("myStorageFile.txt", bucket="testbucket") == True
assert storage.file_changed("myStorageFile.txt", bucket="testbucket") == False

# Write new content to file
time.sleep(1) # FIXME: last_modified attribute of S3Storage only retruns second resolution...
storage.write_to_file("myStorageFile.txt", "!egarotS3S olleH", bucket="testbucket")

# If file has changed (which it should at this point), download it...
if storage.file_changed("myStorageFile.txt", bucket="testbucket"):
    print("Info: myStorageFile.txt has changed - downloading it again...")
    storage.get_file("myLocalStorageFile.txt", "myStorageFile.txt", bucket="testbucket")

f = open("myLocalStorageFile.txt", "r")
content = f.read()

assert content == "!egarotS3S olleH"
print(content)








