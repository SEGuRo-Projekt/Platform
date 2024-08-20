# SPDX-FileCopyrightText: 2023-2024Philipp Jungkamp, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import logging
import sys
import argparse
from io import BytesIO
from dataclasses import dataclass
from queue import Queue
from asn1crypto import tsp
from rfc3161ng import TimeStampResp, oid_to_hash

from seguro.common import broker, store, config


@dataclass
class TSRMessage:
    algorithm: str
    digest: bytes
    tsr: TimeStampResp
    payload: bytes

    @classmethod
    def decode(cls, msg: broker.Message) -> "TSRMessage":
        """Decode a MQTT message into a TSR message

        Args:
          msg: The MQTT message

        Returns:
            TSRMessage: The decoded TSR message
        """

        tsr = tsp.TimeStampResp.load(msg.payload, strict=True)
        tst_info = tsr["time_stamp_token"]["signed_data"][
            "encap_content_info"
        ].parsed
        imprint: tsp.MessageImprint = tst_info["message_imprint"]

        return cls(
            imprint["hash_algorithm"],
            imprint["hashed_message"],
            tsr,
            msg.payload,
        )


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument("-t", "--topic", type=str, default="signatures")
    parser.add_argument("-p", "--prefix", type=str, default="signatures")
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

    queue: Queue = Queue()
    b = broker.Client("signature-recorder")
    s = store.Client()

    def tsr_callback(_b: broker.Client, msg: broker.Message):
        try:
            queue.put(TSRMessage.decode(msg))
        except Exception as err:
            logging.error(f"Failed to receive TSR: {err}")

    def sig_callback(_b: broker.Client, msg: broker.Message):
        try:
            queue.put(TSRMessage.decode(msg))
        except Exception as err:
            logging.error(f"Failed to receive TSR: {err}")

    b.subscribe(args.topic + "/tsr", tsr_callback)
    b.subscribe(args.topic + "/sig", sig_callback)

    msg: TSRMessage
    while (msg := queue.get()) is not None:
        algorithm = msg.algorithm
        digest_hex = msg.digest.hex().upper()
        logging.info(f"Received TSR for {algorithm}:{digest_hex}")

        s.client.put_object(
            bucket_name=s.bucket,
            object_name=f"tsr/{digest_hex}.{algorithm}.tsr",
            data=BytesIO(msg.payload),
            length=len(msg.payload),
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
