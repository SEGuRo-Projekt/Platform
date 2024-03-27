#!/usr/bin/env python
# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import sys
import logging
import os
from pprint import pformat

import minio
import minio.credentials

BUCKETS = ["seguro", "registry"]


def main() -> int:
    logging.basicConfig(
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
        level=logging.INFO,
    )

    minio_user = os.environ.get("MINIO_ROOT_USER", "")
    minio_pass = os.environ.get("MINIO_ROOT_PASSWORD", "")
    minio_endpoint = "minio:9000"
    minio_url = f"http://{minio_endpoint}"

    logging.info("Create host alias")
    os.system(
        f"mc config host add minio {minio_url} {minio_user} {minio_pass}"
    )

    creds = minio.credentials.StaticProvider(minio_user, minio_pass)
    mc = minio.Minio(minio_endpoint, credentials=creds, secure=False)
    mca = minio.MinioAdmin(minio_endpoint, credentials=creds, secure=False)

    logging.info("Server info: %s", pformat(mca.info()))

    for bucket in BUCKETS:
        if mc.bucket_exists(bucket):
            logging.info(f"Bucket {bucket} already exists")
        else:
            logging.info(f"Creating bucket {bucket}:")
            mc.make_bucket(bucket)

    return 0


if __name__ == "__main__":
    sys.exit(main())
