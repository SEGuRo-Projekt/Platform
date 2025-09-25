# SPDX-FileCopyrightText: 2023-2024Philipp Jungkamp, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import sys
import re
import os
import json
import argparse
import logging
import environ
import urllib.parse
import apprise
from apprise.attachment.http import AttachHTTP as AppriseAttachHTTP
from pathlib import Path
from queue import SimpleQueue

from seguro.common import broker, store, config
from seguro.commands.notifier import model

env = environ.Env()

TOPIC = env.str("TOPIC", "notifications")
CONFIG_PATHS = env.list("CONFIG", str, [])


def env_substitute(s: str) -> str:
    def repl(m: re.Match) -> str:
        var = m.group(1)
        return os.environ.get(var, "")

    return re.sub(r"\$\{([A-Z_]+)\}", repl, s)


class AttachHTTP(AppriseAttachHTTP):
    def __init__(self, url, verify_certificate=True):
        result = AppriseAttachHTTP.parse_url(url)

        logging.info("Result: %s", result)

        super().__init__(**result)

        pr = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(pr.query)

        self.qsd = {k: v[0] for k, v in qs.items()}

        self.verify_certificate = verify_certificate


class Notifier:
    def __init__(self, config_paths: list[str], topic: str):
        self.logger = logging.getLogger("notifier")

        self.queue: SimpleQueue[model.Notification] = SimpleQueue()
        self.apprise = apprise.Apprise()

        self.broker = broker.Client("notifier")
        self.store = store.Client()

        self.apprise.add(self._get_config(config_paths))

        self.broker.subscribe(topic, self._on_message)

        self.logger.info("Sending test notification")
        test_notification = model.Notification(
            title="Notifier started",
            body="Notifier service has been started",
            tag="admins",
        )
        self.publish_notification(test_notification)

    def publish_notification(self, notification: model.Notification):
        self.logger.info(f"Received notification for tag: {notification.tag}")
        self.logger.debug(f"\t{notification}")

        notification, attach = self._add_attachments(notification)

        self.apprise.notify(
            body=notification.body,
            title=notification.title,
            tag=notification.tag,
            notify_type=notification.notify_type,  # type: ignore
            body_format=notification.body_format,  # type: ignore
            attach=attach,
        )

    @staticmethod
    def _get_config(config_paths: list[str]) -> apprise.AppriseConfig:
        cfg = apprise.AppriseConfig()
        s = store.Client()

        for config_path in config_paths:
            logging.info("Reading store config from: %s", config_path)

            if config_path.startswith("s3://"):
                config_content = (
                    s.client.get_object(
                        config.S3_BUCKET, config_path.removeprefix("s3://")
                    )
                    .read()
                    .decode("utf-8")
                )

            else:
                with open(config_path) as f:
                    config_content = f.read()

            config_content = env_substitute(config_content)

            cfg.add_config(config_content, format="yaml")

        return cfg

    def _on_message(self, _b: broker.Client, msg: broker.Message):
        """Callback which gets called for each message received on the
        MQTT notification topic.

        Args:
          _broker: The MQTT client
          msg: The MQTT message

        """

        notification_dict = json.loads(msg.payload)
        notification = model.Notification(**notification_dict)

        self.queue.put(notification)

    def _add_attachments(
        self,
        notification: model.Notification,
    ):
        if len(notification.attachments) == 0:
            return notification, None

        attach = apprise.AppriseAttachment()
        urls = []

        for att in notification.attachments:
            if not isinstance(att, model.StoreAttachment):
                logging.warn("Ignoring non-store attachment")
                continue

            url = self.store.get_file_url(
                att.object_name,
                expires=att.expires,
                public=not att.inline,
            )

            self.logger.info("URL: %s", url)

            if att.inline:
                attach.add(AttachHTTP(url))  # type: ignore
            else:
                path = Path(att.object_name)
                urls.append((url, path.name))

        if len(urls) > 0:
            if notification.body_format == "html":
                footer = "<br/><h3>Attachments</h3><ul>"

                for url, name in urls:
                    footer += f'<li><a href="{url}">{name}</a></li>'

                footer += "</ul>"
            else:
                footer = "\n\n### Attachments\n"

                for url, name in urls:
                    footer += f"  - [{name}]({url})\n"

            notification.body += footer

        return notification, attach

    def run(self):
        while True:
            try:
                notification = self.queue.get()
                self.publish_notification(notification)
            except Exception as err:
                logging.error(f"{err}")
            except KeyboardInterrupt:
                break


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument("-t", "--topic", type=str, default=TOPIC)
    parser.add_argument(
        "-c",
        "--config",
        dest="config_paths",
        type=str,
        nargs="+",
        default=CONFIG_PATHS,
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

    notifier = Notifier(args.config_paths, args.topic)
    notifier.run()

    return 0


if __name__ == "__main__":
    sys.exit(main())
