# SPDX-FileCopyrightText: 2024-2025 Lukas Lenz, RWTH Aachen
# SPDX-License-Identifier: Apache-2.0

import sys
import time
import environ
import pandapower as pp
import paho.mqtt.client as mqtt
from villas.node.formats import Sample

from seguro.common import broker

Message = mqtt.MQTTMessage

env = environ.Env()

# Authentication
TOPIC = env.str("TOPIC", "data/measurements/demo-data")
RATE = env.float("RATE", 10.0)
VALUES = env.int("VALUES", 6)
BLOCK_INTERVAL = env.str("BLOCK_INTERVAL", "1m")
SAMPLE_TYPE = env.str("SAMPLE_TYPE", "simple")

# Grid
net = pp.from_json("cim/seguro_split_net_1.json")

# thresholds_upper = [235, 235, 235, 24, 24, 24, 5500, 5500, 5500]
# thresholds_lower = [225, 225, 225, 22, 22, 22, 5200, 5200, 5200]
thresholds_upper = 235
thresholds_lower = 225


def printMessage(samples: list[Sample]):
    print("U1 : " + str(samples[-1].data[0]))
    print("U2 : " + str(samples[-1].data[1]))
    print("U3 : " + str(samples[-1].data[2]))
    print("I1 : " + str(samples[-1].data[3]))
    print("I2 : " + str(samples[-1].data[4]))
    print("I3 : " + str(samples[-1].data[5]))
    print("P1 : " + str(samples[-1].data[6]))
    print("P2 : " + str(samples[-1].data[7]))
    print("P3 : " + str(samples[-1].data[8]))
    print("F : " + str(samples[-1].data[9]))


def threshold(samples: list[Sample]):
    for i in range(len(samples[-1].data)):
        if (
            samples[-1].data[i].real > thresholds_upper
            or samples[-1].data[i].real < thresholds_lower
        ):
            print("Out of bounds: " + str(i))


def stabilize(samples, x):
    std_dev = 0.01  # Standard deviation
    print("Message ID: " + str(samples[0]))
    for i in range(1, len(samples)):
        pp.create.create_measurement(
            net, "v", "bus", samples[i].real, std_dev, i
        )
    for i in range(1, len(samples)):
        pp.create.create_measurement(
            net, "v", "bus", samples[i].real, std_dev, i
        )
    print("created all measurements - running state estimation now")
    success = pp.estimation.estimate(net, init="flat")
    print(success)
    print(net.res_bus)


def thresholds(samples):
    # print(samples)
    # print(samples[0])
    # print(len(samples))

    # Convert strings to complex
    for i in range(1, len(samples)):
        samples[i] = complex(samples[i])

    for i in range(1, len(samples)):
        if (
            samples[i].real > thresholds_upper
            or samples[i].real < thresholds_lower
        ):
            print(
                samples[0]
                + ": Out of bounds: "
                + str(i)
                + " : "
                + str(samples[i].real)
            )
            stabilize(samples, i)
        # else:
        #     print(samples[0] + ": Ok")


def callback(b: broker.Client, topic: str, samples: list[Sample]):
    print("New MQTT Message:")
    printMessage(samples)
    threshold(samples)


def main():
    # Command line arguments
    input_file = None

    if len(sys.argv) > 1:
        print(sys.argv[1])
        input_file = sys.argv[1]

        with open(input_file, "r") as f:
            next(f)
            for line in f:
                line_data = line.split(",")
                thresholds(line_data)

        return 0
    else:
        # Initialize broker
        b = broker.Client(uid="demo-data")

        # Subscribe to topic with callback function
        b.subscribe_samples(TOPIC, callback)

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break

    return 0


if __name__ == "__main__":
    main()
