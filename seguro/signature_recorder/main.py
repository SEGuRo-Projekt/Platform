"""
SPDX-FileCopyrightText: 2023 Philipp Jungkamp, OPAL-RT Germany GmbH
SPDX-License-Identifier: Apache-2.0
"""  # noqa: E501

import logging
from io import BytesIO
from dataclasses import dataclass
from queue import Queue
from pyasn1.codec import der
from rfc3161ng import TimeStampResp, oid_to_hash
from seguro.common.broker import BrokerClient, Message
from seguro.common.store import Client as StoreClient


@dataclass
class TSRMessage:
    algorithm: str
    digest: bytes
    tsr: TimeStampResp
    payload: bytes

    @staticmethod
    def decode(msg: Message) -> "TSRMessage":
        tsr, tail = der.decoder.decode(msg.payload, asn1Spec=TimeStampResp())
        assert not tail
        imprint = tsr.time_stamp_token.tst_info.message_imprint
        algorithm: str = oid_to_hash[imprint["hashAlgorithm"]["algorithm"]]
        digest: bytes = imprint["hashedMessage"].asOctets()
        return TSRMessage(algorithm, digest, tsr, msg.payload)


def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s.%(msecs)03d %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    queue: Queue = Queue()
    broker = BrokerClient("signature-recorder")
    store = StoreClient()

    def tsr_callback(_broker, msg):
        try:
            queue.put(TSRMessage.decode(msg))
        except Exception as err:
            logging.error(f"Failed to receive TSR: {err}")

    broker.subscribe("signatures/tsr", tsr_callback)

    msg: TSRMessage
    while (msg := queue.get()) is not None:
        algorithm = msg.algorithm
        digest_hex = msg.digest.hex().upper()
        logging.info(f"Received TSR for {algorithm}:{digest_hex}")

        store.client.put_object(
            bucket_name=store.bucket,
            object_name=f"tsr/{digest_hex}.{algorithm}.tsr",
            data=BytesIO(msg.payload),
            length=len(msg.payload),
        )


if __name__ == "__main__":
    main()
