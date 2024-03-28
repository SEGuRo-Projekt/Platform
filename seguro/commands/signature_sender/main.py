"""
SPDX-FileCopyrightText: 2023 Philipp Jungkamp, OPAL-RT Germany GmbH
SPDX-License-Identifier: Apache-2.0
"""  # noqa: E501

import sys
import argparse
import dataclasses as dc
import logging
import multiprocessing as mp
from pathlib import Path

from pyasn1.codec import der
from rfc3161ng import RemoteTimestamper
from villas.node.digest import Digest

from seguro.common import broker


@dc.dataclass
class PipeWorker:
    path: Path
    queue: mp.Queue = dc.field(default_factory=mp.Queue)
    worker: mp.Process = dc.field(init=False)

    def __post_init__(self):
        def run():
            self.__run()

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

    parser.add_argument("-t", "--topic", type=str, default="signatures/tsr")
    parser.add_argument("-u", "--uid", type=str, default="ms1")
    parser.add_argument("-f", "--fifo", type=str, default="digest.fifo")
    parser.add_argument(
        "-l",
        "--log-level",
        default="info",
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
    client = broker.Client(f"signature-sender/{args.uid}")
    tsa = RemoteTimestamper("https://freetsa.org/tsr", hashname="sha256")

    with pipe:
        while (digest := pipe.queue.get()) is not None:
            logging.info(f"Received {digest.dump()=}")
            client.publish("signatures/digest", digest.dump())

            algorithm = digest.algorithm
            digest_hex = digest.bytes.hex().upper()

            try:
                assert digest.algorithm == tsa.hashname
                # Adding return_tsr=True makes this function return the whole
                # timestamp response instead of just the timestamp token.
                tsr = tsa(digest=digest.bytes, return_tsr=True)

                logging.info(f"Received TSR for {algorithm}:{digest_hex}")

                client.publish(args.topic, der.encoder.encode(tsr))
            except Exception as err:
                logging.error(
                    f"Failed to produce TSR for {algorithm}:{digest_hex} {err}"  # noqa: E501
                )

                continue

        logging.debug("Closing pipe")

    return 0


if __name__ == "__main__":
    sys.exit(main())
