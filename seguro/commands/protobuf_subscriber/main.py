# SPDX-FileCopyrightText: 2024 Felix Wege, EONERC-ACS, RWTH Aachen University
# SPDX-License-Identifier: Apache-2.0

import sys
import socket
import argparse
import time

from seguro.common import config
from seguro.common.broker import Client, Sample


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument("-H", "--host", type=str, default=config.MQTT_HOST)
    parser.add_argument("-p", "--port", type=int, default=config.MQTT_PORT)
    parser.add_argument("-c", "--cafile", type=str, default=config.TLS_CACERT)
    parser.add_argument("-C", "--cert", type=str, default=config.TLS_CERT)
    parser.add_argument("-k", "--key", type=str, default=config.TLS_KEY)
    parser.add_argument("-t", "--topic", type=str, default=None)
    parser.add_argument(
        "-i", "--id", type=str, default=socket.gethostname() + "-sub"
    )
    args = parser.parse_args()

    b = Client(
        uid=args.id,
        host=args.host,
        port=args.port,
        tls_cert=args.cert,
        tls_key=args.key,
        tls_cacert=args.cafile,
    )

    def callback(b: Client, topic: str, samples: list[Sample]):
        """Callback which gets called for each received MQTT message

        Args:
          client: The broker client
          msg: The MQTT message

        """
        print(samples)

    b.subscribe_samples(args.topic, callback)

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break

    return 0


if __name__ == "__main__":
    sys.exit(main())
