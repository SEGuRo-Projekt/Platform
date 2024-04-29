# SPDX-FileCopyrightText: 2023-2024 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import pydantic
import datetime
from abc import ABC


class AttachmentBase(pydantic.BaseModel, ABC):
    inline: bool = False
    expires: datetime.timedelta = datetime.timedelta(days=7)


class StoreAttachment(AttachmentBase):
    object_name: str


class RawAttachment(AttachmentBase):
    name: str
    contents: bytes


class FileAttachment(AttachmentBase):
    file: pydantic.FilePath


Attachment = StoreAttachment | RawAttachment | FileAttachment


class Notification(pydantic.BaseModel):
    body: str
    title: str = ""
    notify_type: str = "info"
    body_format: str = "text"
    attachments: list[Attachment] = []
    tag: str | list[str | list[str]] = "all"
