"""
SPDX-FileCopyrightText: 2023 Felix Wege, EONERC-ACS, RWTH Aachen University
SPDX-License-Identifier: Apache-2.0
"""

import io

from minio import Minio
from seguro.common.config import (
    S3_ACCESS_KEY,
    S3_HOST,
    S3_PORT,
    S3_REGION,
    S3_SECRET_KEY,
    S3_SECURE,
)


class Store:
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
        self.tracked_files = {}
        self.client = Minio(
            endpoint=f"{host}:{port}",
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
            region=region,
        )

    def get_file(self, filename, file, bucket="seguro"):
        """Download file from the S3 object store and store it locally.

        Arguments:
            filename -- Local filename that is used
            file     -- Name of requested file in storage

        Keyword arguments:
            bucket -- Storage bucket that is considered (default "seguro")
        """
        if not self.client.bucket_exists(bucket):
            print(f"Error: Bucket {bucket} does not exist...")
            return

        self.client.fget_object(bucket, file, filename)

    def put_file(self, filename, file, bucket="seguro"):
        """Upload local file and store it in the S3Storage.

        Arguments:
            filename -- Name of uploaded file in storage
            file     -- Local file that is used

        Keyword arguments:
            bucket -- Storage bucket that is considered (default "seguro")
        """
        if not self.client.bucket_exists(bucket):
            print(f"Error: Bucket {bucket} does not exist...")
            return

        self.client.fput_object(bucket, filename, file)

    def write_to_file(self, filename, content, bucket="seguro"):
        """Write to file stored it in the S3Storage.

        Arguments:
            filename -- Name of file in storage
            content  -- Content that is written to file

        Keyword arguments:
            bucket -- Storage bucket that is considered (default "seguro")
        """
        if not self.client.bucket_exists(bucket):
            print(f"Error: Bucket {bucket} does not exist...")
            return

        self.client.put_object(
            bucket,
            filename,
            io.BytesIO(b"%b" % content.encode("utf8")),
            len(content),
        )

    def file_changed(self, filename, bucket="seguro"):
        """Check if file has changed since last call.

        Arguments:
            filename -- Local filename that is used

        Keyword arguments:
            bucket -- Storage bucket that is considered (default "seguro")

        Returns:
            True  -- If file has changed or if file untracked
            False -- Else
        """
        if not self.client.bucket_exists(bucket):
            print(f"Error: Bucket {bucket} does not exist...")
            return

        stats = self.client.stat_object(bucket, filename)

        if filename not in self.tracked_files.keys():
            self.tracked_files[filename] = stats._last_modified
            # if file is not tracked yet, assume it has changed
            return True

        if self.tracked_files[filename] != stats._last_modified:
            print(self.tracked_files[filename])
            print(stats._last_modified)
            self.tracked_files[filename] = stats._last_modified
            return True

        print(self.tracked_files[filename])
        print(stats._last_modified)
        return False
