"""
SPDX-FileCopyrightText: 2023 Felix Wege, EONERC-ACS, RWTH Aachen University
SPDX-License-Identifier: Apache-2.0
"""

import io
import threading
import enum

from minio import Minio

import seguro.common.logger
from seguro.common.config import (
    S3_ACCESS_KEY,
    S3_HOST,
    S3_PORT,
    S3_REGION,
    S3_SECRET_KEY,
    S3_SECURE,
    S3_BUCKET,
    LOG_LEVEL,
    MAX_BYTES,
    BACKUP_COUNT,
)


class EventType(enum.Flag):
    CREATED = enum.auto()
    REMOVED = enum.auto()


class Event:
    def __init__(self, event):
        records = event.get("Records")
        record = records[0]

        event_name: str = record.get("eventName")
        s3: dict = record.get("s3", {})
        obj: str = s3.get("object", {})

        self.filename: str = obj.get("key")

        if event_name.startswith("s3:ObjectCreated"):
            self.type = EventType.CREATED
        elif event_name.startswith("s3:ObjectRemoved"):
            self.type = EventType.REMOVED

    def __str__(self) -> str:
        return f"{self.filename} {self.type.name}"


class Client:
    """Helper class for S3 object store interaction with the SEGuRo platform

    This class provides an abstraction layer for interactions between
    the S3 data store and the SEGuRo platform.
    """

    def __init__(
        self,
        host=S3_HOST,
        port=S3_PORT,
        access_key=S3_ACCESS_KEY,
        secret_key=S3_SECRET_KEY,
        secure=S3_SECURE,
        region=S3_REGION,
        bucket=S3_BUCKET,
        log_level=LOG_LEVEL,
        log_max_bytes=MAX_BYTES,
        log_backup_count=BACKUP_COUNT,
    ):
        """Store Constructor

        Connect to an S3 object store using the given credentials and store the
        returned client handle.

        Arguments:
            server      -- Hostname or IP address of the storage server
            port        -- Network port of the storage server
            access_key  -- Access key (UID) for authentication
            secret_key  -- Secret key (password) for authentication
        """
        self.bucket = bucket

        self.client = Minio(
            endpoint=f"{host}:{port}",
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
            region=region,
        )

        if not self.client.bucket_exists(self.bucket):
            raise Exception(f"Error: Bucket {self.bucket} does not exist...")

        self.logger = seguro.common.logger.init_logger(
            log_level,
            os.path.join(
                os.path.dirname(__file__),
                "../../log/storeclient/storeclient.log",
            ),
            max_bytes=log_max_bytes,
            backup_count=log_backup_count,
        )

    def get_file(self, filename, file):
        """Download file from the S3 object store and store it locally.

        Arguments:
            filename -- Local filename that is used
            file     -- Name of requested file in storage
        """
        return self.client.fget_object(self.bucket, file, filename)

    def put_file(self, filename, file):
        """Upload local file and store it in the S3Storage.

        Arguments:
            filename -- Name of uploaded file in storage
            file     -- Local file that is used
        """
        return self.client.fput_object(self.bucket, filename, file)

    def remove_file(self, filename):
        """Remove a local file from the S3Storage.

        Arguments:
            filename -- Name of removed file in storage
        """
        return self.client.remove_object(self.bucket, filename)

    def put_file_contents(self, filename, content):
        """Write to file stored it in the S3Storage.

        Arguments:
            filename -- Name of file in storage
            content  -- Content that is written to file
        """
        if not self.client.bucket_exists(self.bucket):
            raise Exception(f"Error: Bucket {self.bucket} does not exist...")

        return self.client.put_object(
            self.bucket,
            filename,
            io.BytesIO(b"%b" % content.encode("utf8")),
            len(content),
        )

    def watch(self, prefix: str, events=EventType.CREATED | EventType.REMOVED):
        s3_events = []
        if EventType.CREATED in events:
            s3_events.append("s3:ObjectCreated:*")
        if EventType.REMOVED in events:
            s3_events.append("s3:ObjectRemoved:*")

        with self.client.listen_bucket_notification(
            self.bucket,
            prefix=prefix,
            events=s3_events,
        ) as events:
            for event in events:
                yield Event(event)

    def watch_async(
        self,
        prefix: str,
        cb: callable,
        events=EventType.CREATED | EventType.REMOVED,
    ):
        return Watcher(self, prefix, cb, events)


class Watcher(threading.Thread):
    """Helper class for asynchronous watching of of S3 objects"""
    def __init__(
        self, client: Client, prefix: str, cb: callable, events: EventType
    ):
        super().__init__()

        self.events = client.watch(prefix, events)
        self.cb = cb
        self._stopflag = threading.Event()

        self.start()

    def run(self):
        for event in self.events:
            if self._stopflag.is_set():
                break

            try:
                self.cb(event)
            except StopIteration:
                break

    def stop(self):
        self._stopflag.set()
