"""
SPDX-FileCopyrightText: 2023 Felix Wege, EONERC-ACS, RWTH Aachen University
SPDX-License-Identifier: Apache-2.0
"""

import io
import threading
import enum
import logging
import http.client
import minio
import pandas as pd
from typing import Callable

from seguro.common.config import (
    S3_ACCESS_KEY,
    S3_HOST,
    S3_PORT,
    S3_REGION,
    S3_SECRET_KEY,
    S3_SECURE,
    S3_BUCKET,
)


class Event(enum.Flag):
    UNKNOWN = enum.auto()
    CREATED = enum.auto()
    REMOVED = enum.auto()


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
    ):
        """Store Constructor

        Connect to an S3 object store using the given credentials and store the
        returned client handle.

        Arguments:
            uid         -- Unique id/name of the store client
            host        -- Hostname or IP address of the storage server
            port        -- Network port of the storage server
            access_key  -- Access key (UID) for authentication
            secret_key  -- Secret key (password) for authentication
        """

        self.logger = logging.getLogger(__name__)
        self.bucket = bucket
        self.client = minio.Minio(
            endpoint=f"{host}:{port}",
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
            region=region,
        )

        # Used by Pandas
        self.storage_options = {
            "endpoint_url": f"http{'s' if secure else ''}://{host}:{port}",
            "use_ssl": secure,
            "key": access_key,
            "secret": secret_key,
            "client_kwargs": {"region_name": region},
        }

        if not self.client.bucket_exists(self.bucket):
            raise Exception(f"Error: Bucket {self.bucket} does not exist...")

    def get_file(self, filename: str, file: str):
        """Download file from the S3 object store and store it locally.

        Arguments:
            filename -- Local filename that is used
            file     -- Name of requested file in storage
        """
        return self.client.fget_object(self.bucket, file, filename)

    def put_file(self, filename: str, file: str):
        """Upload local file and store it in the S3Storage.

        Arguments:
            filename -- Name of uploaded file in storage
            file     -- Local file that is used
        """
        return self.client.fput_object(self.bucket, filename, file)

    def remove_file(self, filename: str):
        """Remove a local file from the S3Storage.

        Arguments:
            filename -- Name of removed file in storage
        """
        return self.client.remove_object(self.bucket, filename)

    def put_file_contents(self, filename: str, content: str):
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

    def get_file_contents(self, filename: str) -> http.client.HTTPResponse:
        """Write to file stored it in the S3Storage.

        Arguments:
            filename -- Name of file in storage
            content  -- Content that is written to file
        """
        if not self.client.bucket_exists(self.bucket):
            raise Exception(f"Error: Bucket {self.bucket} does not exist...")

        return self.client.get_object(self.bucket, filename)

    def put_frame(self, filename: str, df: pd.DataFrame):
        df.to_parquet(
            f"s3://{self.bucket}/{filename}",
            compression="zstd",
            storage_options=self.storage_options,
        )

    def get_frame(self, filename: str) -> pd.DataFrame:
        return pd.read_parquet(
            f"s3://{self.bucket}/{filename}",
            storage_options=self.storage_options,
        )

    def watch(
        self,
        prefix: str,
        events: Event = Event.CREATED | Event.REMOVED,
        initial: bool = False,
    ):
        s3_events = []
        if Event.CREATED in events:
            s3_events.append("s3:ObjectCreated:*")
        if Event.REMOVED in events:
            s3_events.append("s3:ObjectRemoved:*")

        if initial and Event.CREATED in events:
            objs = self.client.list_objects(
                self.bucket, prefix=prefix, recursive=True
            )
            for obj in objs:
                yield Event.CREATED, obj.object_name

        with self.client.listen_bucket_notification(
            self.bucket,
            prefix=prefix,
            events=s3_events,
        ) as events:
            for event in events:
                yield _decode_event(event)

    def watch_async(
        self,
        prefix: str,
        cb: Callable[[Event, str], None],
        events=Event.CREATED | Event.REMOVED,
        initial: bool = False,
    ):
        return Watcher(self, prefix, cb, events, initial)


class Watcher(threading.Thread):
    """Helper class for asynchronous watching of of S3 objects"""

    def __init__(
        self,
        client: Client,
        prefix: str,
        cb: Callable[[Client, Event, str], None],
        events: Event = Event.CREATED | Event.REMOVED,
        initial: bool = False,
    ):
        super().__init__()

        self.cb = cb
        self.client = client
        self._stopflag = threading.Event()

        s3_events = []
        if Event.CREATED in events:
            s3_events.append("s3:ObjectCreated:*")
        if Event.REMOVED in events:
            s3_events.append("s3:ObjectRemoved:*")

        if initial and Event.CREATED in events:
            objs = self.client.client.list_objects(
                self.client.bucket, prefix=prefix, recursive=True
            )
            for obj in objs:
                cb(self.client, Event.CREATED, obj.object_name)

        self.events = self.client.client.listen_bucket_notification(
            self.client.bucket,
            prefix=prefix,
            events=s3_events,
        )

        self.start()

    def run(self):
        while True:
            try:
                event = next(self.events)

            # AttributeError is raised because we
            # set self.events._response to None in Watcher.stop()
            except AttributeError:
                break

            if self._stopflag.is_set():
                break

            try:
                typ, filename = _decode_event(event)
                self.cb(self.client, typ, filename)
            except StopIteration:
                break

    def stop(self):
        self._stopflag.set()
        self.events._close_response()
        self.join()


def _decode_event(event) -> tuple[Event, str]:
    records = event.get("Records")
    record = records[0]

    event_name: str = record.get("eventName")
    s3: dict = record.get("s3", {})
    obj = s3.get("object", {})

    filename: str = obj.get("key")

    if event_name.startswith("s3:ObjectCreated"):
        typ = Event.CREATED
    elif event_name.startswith("s3:ObjectRemoved"):
        typ = Event.REMOVED
    else:
        typ = Event.UNKNOWN

    return typ, filename
