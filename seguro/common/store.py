# SPDX-FileCopyrightText: 2023 Felix Wege, EONERC-ACS, RWTH Aachen University
# SPDX-License-Identifier: Apache-2.0

import io
import threading
import enum
import logging
import minio
import minio.credentials
import urllib3
import pandas as pd
from typing import Callable

from seguro.common import config


class Event(enum.Flag):
    UNKNOWN = enum.auto()
    CREATED = enum.auto()
    REMOVED = enum.auto()

    def __str__(self):
        if self.name:
            return self.name.lower()

        return ""


class Client:
    """Helper class for S3 object store interaction with the SEGuRo platform

    This class provides an abstraction layer for interactions between
    the S3 data store and the SEGuRo platform.

    Connect to an S3 object store using the given credentials and store the
    returned client handle.

    Args:
        host: Hostname or IP address of the storage server
        port: Network port of the storage server
        tls_cert: File containing the TLS client certificate for mutual TLS
                    authentication.
        tls_key: File containing the TLS client key for mutual TLS
                authentication.
        tls_cacert: File containing the TLS certificate authority to validate
                    the servers certificate against.
        secure: Establish secure connection via TLS
        region: The S3 region
        bucket: The S3 bucket

    """

    def __init__(
        self,
        host: str = config.S3_HOST,
        port: int = config.S3_PORT,
        tls_cacert: str = config.TLS_CACERT,
        tls_cert: str = config.TLS_CERT,
        tls_key: str = config.TLS_KEY,
        region: str = config.S3_REGION,
        bucket: str = config.S3_BUCKET,
    ):
        self.logger = logging.getLogger(__name__)
        self.bucket = bucket

        http_client = urllib3.PoolManager(
            cert_reqs="CERT_REQUIRED", ca_certs=tls_cacert
        )

        self.creds = minio.credentials.CertificateIdentityProvider(
            sts_endpoint=f"https://{host}:{port}",
            cert_file=tls_cert,
            key_file=tls_key,
            ca_certs=tls_cacert,
        )
        self.client = minio.Minio(
            endpoint=f"{host}:{port}",
            region=region,
            credentials=self.creds,
            http_client=http_client,
        )

        # Used by Pandas
        creds = self.creds.retrieve()
        self.storage_options = {
            "endpoint_url": f"https://{host}:{port}",
            "use_ssl": True,
            "client_kwargs": {
                "aws_access_key_id": creds.access_key,
                "aws_secret_access_key": creds.secret_key,
                "aws_session_token": creds.session_token,
                "region_name": region,
                "verify": tls_cacert,
            },
        }

        if not self.client.bucket_exists(self.bucket):
            raise Exception(f"Error: Bucket {self.bucket} does not exist...")

    def get_file(self, filename: str, file: str):
        """Download file from the S3 object store and store it locally.

        Args:
          filename: Local filename that is used
          file: Name of requested file in storage
          filename: str:
          file: str:

        Returns:

        """
        return self.client.fget_object(self.bucket, file, filename)

    def put_file(self, filename: str, file: str):
        """Upload local file and store it in the S3Storage.

        Args:
          filename: Name of uploaded file in storage
          file: Local file that is used
          filename: str:
          file: str:

        Returns:

        """
        return self.client.fput_object(self.bucket, filename, file)

    def remove_file(self, filename: str):
        """Remove a local file from the S3Storage.

        Args:
          filename: Name of removed file in storage
          filename: str:

        Returns:

        """
        return self.client.remove_object(self.bucket, filename)

    def put_file_contents(self, filename: str, content: bytes):
        """Write to file stored it in the S3Storage.

        Args:
          filename: Name of file in storage
          content: Content that is written to file
          filename: str:
          content: bytes:

        Returns:

        """
        if not self.client.bucket_exists(self.bucket):
            raise Exception(f"Error: Bucket {self.bucket} does not exist...")

        return self.client.put_object(
            self.bucket,
            filename,
            io.BytesIO(content),
            len(content),
        )

    def get_file_contents(self, filename: str) -> urllib3.BaseHTTPResponse:
        """Write to file stored it in the S3Storage.

        Args:
          filename: Name of file in storage
          content: Content that is written to file
          filename: str:

        Returns:

        """
        if not self.client.bucket_exists(self.bucket):
            raise Exception(f"Error: Bucket {self.bucket} does not exist...")

        return self.client.get_object(self.bucket, filename)

    def put_frame(self, filename: str, df: pd.DataFrame):
        """Upload a Pandas Dataframe as a Parquet file to the store

        Args:
          filename: The filename at which it should be stored
          df: The Pandas DataFrame

        Returns:

        """
        df.to_parquet(
            f"s3://{self.bucket}/{filename}",
            compression="zstd",
            storage_options=self.storage_options,
        )

    def get_frame(self, filename: str) -> pd.DataFrame:
        """Download a Pandas Dataframe as a Parquet file to the store

        Args:
          filename: The filename from which it should be retrieved

        Returns:

        """
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
        """

        Args:
          prefix: str:
          events: Event:  (Default value = Event.CREATED | Event.REMOVED)
          initial: bool:  (Default value = False)

        Returns:

        """
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
            events=tuple(s3_events),
        ) as events:
            for event in events:
                yield _decode_event(event)

    def watch_async(
        self,
        prefix: str,
        cb: Callable[["Client", Event, str], None],
        events=Event.CREATED | Event.REMOVED,
        initial: bool = False,
    ):
        """

        Args:
          prefix: str:
          cb: Callable[["Client":
          Event:
          str]:
          None]:
          events:  (Default value = Event.CREATED | Event.REMOVED)
          initial: bool:  (Default value = False)

        Returns:

        """
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
            events=tuple(s3_events),
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
    """

    Args:
      event:

    Returns:

    """
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
