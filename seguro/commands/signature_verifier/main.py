# SPDX-FileCopyrightText: 2023-2024Philipp Jungkamp, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import sys
import argparse
import dataclasses as dc
import logging
import multiprocessing as mp
from pathlib import Path

from pyasn1.codec import der
from rfc3161ng import RemoteTimestamper
from villas.node.digest import Digest

from seguro.common import broker, config


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-t",
        "--topic",
        type=str,
        help="MQTT topic for publishing signatures",
        default="signatures/tsr",
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
        "--uri",
        type=str,
        help="URL of Time Stamp Authority server ",
        default="https://freetsa.org/tsr",
    )
    parser.add_argument(
        "-d",
        "--digest",
        type=str,
        help="Frame digest algorithm",
        default="sha256",
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
    b = broker.Client("signature-verifier")
    tsa = RemoteTimestamper(args.uri, hashname=args.digest)

    with pipe:
        while (digest := pipe.queue.get()) is not None:
            logging.info(f"Received {digest.dump()=}")
            b.publish("signatures/digest", digest.dump())

            algorithm = digest.algorithm
            digest_hex = digest.bytes.hex().upper()

            try:
                assert digest.algorithm == tsa.hashname
                # Adding return_tsr=True makes this function return the whole
                # timestamp response instead of just the timestamp token.
                tsr = tsa(digest=digest.bytes, return_tsr=True)

                logging.info(f"Received TSR for {algorithm}:{digest_hex}")

                b.publish(args.topic, der.encoder.encode(tsr))
            except Exception as err:
                logging.error(
                    f"Failed to produce TSR for {algorithm}:{digest_hex} {err}"  # noqa: E501
                )

                continue

        logging.debug("Closing pipe")

    return 0


if __name__ == "__main__":
    sys.exit(main())
