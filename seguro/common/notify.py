# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import uuid

from seguro.common import broker, store
from seguro.commands.notifier.model import (
    Notification,
    Attachment,
    RawAttachment,
    StoreAttachment,
    FileAttachment,
)
from seguro.commands.notifier.main import TOPIC


def notify(
    body: str,
    title: str = "",
    notify_type: str = "info",
    body_format: str = "text",
    attachments: list[Attachment] = [],
    tag: str | list[str | list[str]] = "all",
):
    b = broker.Client("notify")
    s = store.Client()

    # Upload attachments to store
    for i, att in enumerate(attachments):
        if isinstance(att, RawAttachment):
            att_obj = (
                f"attachments/{uuid.uuid4()}/"
                + "{att.name if att.name else 'raw.bin'}"
            )
            obj = s.put_file_contents(att_obj, att.contents)

        elif isinstance(att, FileAttachment):
            att_obj = f"attachments/{uuid.uuid4()}/{att.file.name}"
            obj = s.put_file(att_obj, att.file.as_posix())

        else:
            continue

        attachments[i] = StoreAttachment(
            inline=att.inline,
            expires=att.expires,
            object_name=obj.object_name,
        )

    b.publish(
        TOPIC,
        Notification(
            body=body,
            title=title,
            notify_type=notify_type,
            body_format=body_format,
            attachments=attachments,
            tag=tag,
        ).model_dump_json(
            exclude_unset=True, exclude_defaults=True, exclude_none=True
        ),
    )
