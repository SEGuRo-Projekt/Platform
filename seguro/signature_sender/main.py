"""
SPDX-FileCopyrightText: 2023 Philipp Jungkamp, OPAL-RT Germany GmbH
SPDX-License-Identifier: Apache-2.0
"""  # noqa: E501

import dataclasses as dc
import logging
import multiprocessing as mp
from pathlib import Path

from pyasn1.codec import der
from rfc3161ng import RemoteTimestamper
from villas.node.digest import Digest

from seguro.common.broker import BrokerClient


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


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    uid = "ms1"
    pipe = PipeWorker(Path("digest.fifo"))
    broker = BrokerClient(f"signature-sender/{uid}")
    tsa = RemoteTimestamper("https://freetsa.org/tsr", hashname="sha256")

    with pipe:
        while (digest := pipe.queue.get()) is not None:
            logging.info(f"Received {digest.dump()=}")
            broker.publish("signatures/digest", digest.dump())

            algorithm = digest.algorithm
            digest_hex = digest.bytes.hex().upper()

            try:
                assert digest.algorithm == tsa.hashname
                # Adding return_tsr=True makes this function return the whole
                # timestamp response instead of just the timestamp token.
                tsr = tsa(digest=digest.bytes, return_tsr=True)

                logging.info(f"Received TSR for {algorithm}:{digest_hex}")

                broker.publish("signatures/tsr", der.encoder.encode(tsr))
            except Exception as err:
                logging.error(
                    f"Failed to produce TSR for {algorithm}:{digest_hex} {err}"  # noqa: E501
                )

                continue

        logging.debug("Closing pipe")


if __name__ == "__main__":
    main()
