# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import pytest

from seguro.common.notify import (  # noqa: F401
    notify,
    RawAttachment,
    FileAttachment,
    StoreAttachment,
)


@pytest.mark.notify
def test_notify():
    notify(
        "This is a test message",
        "Test message",
        notify_type="warning",
        body_format="text",
        attachments=[
            RawAttachment(name="test.txt", contents=b"Test Attachment")
        ],
        tag=["steffen-vogel", "zulip"],
    )


@pytest.mark.notify
def test_notify_inline():
    notify(
        "This is a test message",
        "Test message",
        notify_type="warning",
        body_format="markdown",
        attachments=[
            RawAttachment(
                inline=True, name="test.txt", contents=b"Test Attachment"
            )
        ],
        tag=["steffen-vogel", "zulip"],
    )
