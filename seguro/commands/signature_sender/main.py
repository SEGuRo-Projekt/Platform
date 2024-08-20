# SPDX-FileCopyrightText: 2023-2024Philipp Jungkamp, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import os
import sys
import argparse
import logging
import multiprocessing as mp
from pathlib import Path

from villas.node.digest import Digest

from seguro.common import broker, config
from seguro.common import openssl


class PipeWorker:
    def __init__(self, path: Path):
        def run():
            self.__run()

        self.path = path
        self.queue: mp.Queue = mp.Queue()
        self.worker = mp.Process(target=run)

    def __run(self):
        try:
            with open(self.path, "rt", buffering=1) as f:
                while line := f.readline():
                    self.queue.put(Digest.parse(line))
        except Exception as err:
            logging.error(f"{err}")
        finally:
            self.queue.put(None)

    def __enter__(self) -> "PipeWorker":
        self.worker.start()
        return self

    def __exit__(self, _type, _value, _trace):
        self.worker.terminate()


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-t",
        "--topic",
        type=str,
        help="MQTT topic for publishing signatures",
        default="signatures",
    )
    parser.add_argument(
        "-f",
        "--fifo",
        type=str,
        help="FIFO for receiving frame digests",
        default="/run/villas-digests.fifo",
    )
    parser.add_argument(
        "-u",
        "--tsa-url",
        type=str,
        help="URL of Time Stamp Authority server",
        default="https://freetsa.org/tsr",
    )
    parser.add_argument(
        "-p",
        "--private-key",
        type=str,
        help="PEM-encoded private key",
    )
    parser.add_argument(
        "-T",
        "--tpm2",
        type=bool,
        action="store_true",
        help="Enable TPM2 support",
    )
    parser.add_argument(
        "-l",
        "--log-level",
        default="debug" if config.DEBUG else "info",
        help="Logging level",
        choices=["debug", "info", "warn", "error", "critical"],
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s.%(msecs)03d %(levelname)s %(name)s %(message)s",
        datefmt="%H:%M:%S",
    )

    pipe = PipeWorker(Path(args.fifo))
    b = broker.Client("signature-sender")
    providers = ["default"]

    if args.tpm:
        providers.append("tpm2")

    ssl = openssl.OpenSSL(providers)

    if args.private_key:
        with open(args.private_key, "rb") as f:
            private_key = openssl.PrivateKey.read_pem(f)
    else:
        private_key = None

    with pipe:
        while (digest := pipe.queue.get()) is not None:
            logging.info(f"Received {digest.dump()=}")
            b.publish("signatures/digest", digest.dump())

            algorithm = digest.algorithm
            digest_hex = digest.bytes.hex().upper()

            if args.tsa_url:
                try:
                    tsr = ssl.timestamp_query(args.tsa_url, digest.bytes)

                    logging.info(f"Received TSR for {algorithm}:{digest_hex}")

                    b.publish(args.topic + "/tsr", tsr)
                except Exception as err:
                    logging.error(
                        f"Failed to produce TSR for {algorithm}:{digest_hex} {err}"  # noqa: E501
                    )

            if private_key:
                try:
                    ssl.sign(private_key, digest.bytes, digest.algorithm)

                except Exception as err:
                    logging.error(
                        f"Failed to produce MP signature for {algorithm}:{digest_hex} {err}"  # noqa: E501
                    )

        logging.debug("Closing pipe")

    return 0


if __name__ == "__main__":
    sys.exit(main())
