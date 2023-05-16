#!/usr/bin/env python
# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import logging
import os
from pprint import pformat

import minio

BUCKETS = ["seguro", "registry"]


def main():
    logging.basicConfig(
        format="%(asctime)s %(name)s %(levelname)s: %(message)s", level=logging.INFO
    )

    minio_user = os.environ.get("MINIO_ROOT_USER")
    minio_pass = os.environ.get("MINIO_ROOT_PASSWORD")
    minio_endpoint = "minio:9000"
    minio_url = f"http://{minio_endpoint}"

    logging.info("Create SSH host key")
    os.system("ssh-keygen -q -N " " -t rsa -b 4096 -f /keys/ssh_host_rsa_key")

    logging.info("Create host alias")
    os.system(f"mc config host add minio {minio_url} {minio_user} {minio_pass}")

    mc = minio.Minio(minio_endpoint, minio_user, minio_pass, secure=False)
    mca = minio.MinioAdmin(target="minio")

    logging.info("Server info: %s", pformat(mca.info()))

    for bucket in BUCKETS:
        if mc.bucket_exists(bucket):
            logging.info(f"Bucket {bucket} already exists")
        else:
            logging.info(f"Creating bucket {bucket}:")
            mc.make_bucket(bucket)


if __name__ == "__main__":
    main()
