"""
SPDX-FileCopyrightText: 2023 Felix Wege, EONERC-ACS, RWTH Aachen University
SPDX-License-Identifier: Apache-2.0
"""

from minio import Minio
import io


class S3Storage:
    """Helper class for S3Storage interaction with the SEGuRo platform

        This class provides an abstraction layer for interactions btween
        the S3Storage and the SEGuRo platform.
    """

    def __init__(self, server, port, access_key, secret_key):
        """S3Storage Constructor

            Connect to an S3Storage using the given credentials and store the
            returned client handle.

            Arguments:
                server      -- Hostname or IP address of the storage server
                port        -- Network port of the storage server
                access_key  -- Access key (UID) for authentication
                secret_key  -- Secret key (password) for authentication

        """
        self.tracked_files = {}
        self.client = self.__connect(server, port, access_key, secret_key)

    def __connect(self, server, port, access_key, secret_key):
        client = Minio(endpoint=server+":"+str(port),
                       access_key=access_key,
                       secret_key=secret_key,
                       secure=False)
        return client

    def get_file(self, filename, file, bucket="seguro"):
        """Download file from the S3Storage and store it locally.

        Arguments:
            filename -- Local filename that is used
            file     -- Name of requested file in storage

        Keyword arguments:
            bucket -- Storage bucket that is considered (default "seguro")
        """
        if not self.client.bucket_exists(bucket):
            print(f"Error: Bucket \"{bucket}\" does not exist...")
            return

        self.client.fget_object(
            bucket, file, filename
        )

    def put_file(self, filename, file, bucket="seguro"):
        """Upload local file and store it in the S3Storage.

        Arguments:
            filename -- Name of uploaded file in storage
            file     -- Local file that is used

        Keyword arguments:
            bucket -- Storage bucket that is considered (default "seguro")
        """
        if not self.client.bucket_exists(bucket):
            print(f"Error: Bucket \"{bucket}\" does not exist...")
            return

        self.client.fput_object(
            bucket, filename, file
        )

    def write_to_file(self, filename, content, bucket="seguro"):
        """Write to file stored it in the S3Storage.

        Arguments:
            filename -- Name of file in storage
            content  -- Content that is written to file

        Keyword arguments:
            bucket -- Storage bucket that is considered (default "seguro")
        """
        if not self.client.bucket_exists(bucket):
            print(f"Error: Bucket \"{bucket}\" does not exist...")
            return

        self.client.put_object(
            bucket,
            filename,
            io.BytesIO(b'%b' % content.encode('utf8')), len(content)
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
            print(f"Error: Bucket \"{bucket}\" does not exist...")
            return

        stats = self.client.stat_object(
            bucket, filename
        )

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
