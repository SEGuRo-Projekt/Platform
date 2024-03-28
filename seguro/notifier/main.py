# SPDX-FileCopyrightText: 2023 Philipp Jungkamp, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import dataclasses as dc
import json
import sys
import argparse
import logging
from queue import SimpleQueue

from apprise import Apprise, AppriseConfig, NotifyType

from seguro.common import broker


@dc.dataclass
class Notification:
    tag: str
    payload: bytes

    def _parse_payload(self):
        payload = self.payload.decode("utf-8")

        try:
            d = json.loads(payload)
            assert isinstance(d, dict)
        except Exception:
            raise ValueError(
                f"Expected a JSON dictionary but received: {payload}"  # noqa: E501
            )

        if (body := d.pop("body", None)) is None:
            raise ValueError("Message is missing key 'body'")

        if not isinstance(body, str):
            raise ValueError(f"Unexpected value for 'body'. Received: {body}")

        if (title := d.pop("title", None)) is None:
            raise ValueError("Message is missing key 'title'")

        if not isinstance(title, str):
            raise ValueError(
                f"Unexpected value for 'title'. Received: {title}"
            )

        match d.pop("notify_type", None):
            case None | "info":
                notify_type = NotifyType.INFO
            case "warning":
                notify_type = NotifyType.WARNING
            case "success":
                notify_type = NotifyType.SUCCESS
            case "failure":
                notify_type = NotifyType.FAILURE
            case other:
                raise ValueError(f"Received unknown notify_type: {other}")

        return body, title, notify_type

    def publish(self, apprise: Apprise):
        body, title, notify_type = self._parse_payload()

        apprise.notify(
            body,
            title,
            notify_type=notify_type,
            tag=self.tag,
        )


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument("-p", "--prefix", type=str, default="tsr")
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

    queue: SimpleQueue = SimpleQueue()
    apprise = Apprise()
    config = AppriseConfig("config.yaml")
    client = broker.Client("notifier")

    def notification_callback(_broker, msg: broker.Message):
        assert msg.topic.startswith(f"{args.prefix}/")
        tag = msg.topic.removeprefix(f"{args.prefix}/")
        queue.put(Notification(tag, msg.payload))

    apprise.add(config)
    apprise.notify("Started notification service", tag="debug")
    client.subscribe(f"{args.prefix}/+", notification_callback)

    while True:
        try:
            notification: Notification = queue.get()
            logging.info(f"Received notification for tag: {notification.tag}")
            logging.debug(f"\t{notification}")
            notification.publish(apprise)
        except Exception as err:
            logging.error(f"{err}")
        except KeyboardInterrupt:
            break

    return 0


if __name__ == "__main__":
    sys.exit(main())
