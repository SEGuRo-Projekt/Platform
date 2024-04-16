#!/usr/bin/env python
# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import sys
import logging
import json
import os
import tempfile
from pprint import pformat

import minio
import minio.credentials


POLICIES = {
    "admin": {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": "s3:*",
                "Effect": "Allow",
                "Resource": ["arn:aws:s3:::*"],
            }
        ],
    }
}

BUCKETS = ["seguro", "registry"]


def create_buckets(mc: minio.Minio):
    for bucket in BUCKETS:
        if mc.bucket_exists(bucket):
            logging.info(f"Bucket {bucket} already exists")
        else:
            logging.info(f"Creating bucket {bucket}:")
            mc.make_bucket(bucket)


def create_policies(mca: minio.MinioAdmin):
    for name, policy in POLICIES.items():
        with tempfile.NamedTemporaryFile("w+t") as tf:
            json.dump(policy, tf)
            tf.flush
            tf.seek(0)

        logging.info(f"Creating policy {name}")


def main() -> int:
    logging.basicConfig(
        format="%(asctime)s.%(msecs)03d %(levelname)s %(name)s %(message)s",
        level=logging.INFO,
    )

    minio_user = os.environ.get("ADMIN_USERNAME", "")
    minio_pass = os.environ.get("ADMIN_PASSWORD", "")
    minio_endpoint = "minio:9000"
    minio_url = f"https://{minio_endpoint}"

    logging.info("Create host alias")
    os.system(
        f"mc config host add minio {minio_url} {minio_user} {minio_pass}"
    )

    creds_static = minio.credentials.StaticProvider(minio_user, minio_pass)
    mc = minio.Minio(minio_endpoint, credentials=creds_static)
    mca = minio.MinioAdmin(minio_endpoint, credentials=creds_static)

    logging.info("Server info: %s", pformat(json.loads(mca.info())))

    create_buckets(mc)
    create_policies(mca)

    # Validate mTLS authentication
    creds_cert = minio.credentials.CertificateIdentityProvider(
        sts_endpoint=minio_url,
        cert_file="/certs/client-admin.crt",
        key_file="/keys/client-admin.key",
        ca_certs="/certs/ca.crt",
    )
    mc = minio.Minio(minio_endpoint, credentials=creds_cert)

    if len(mc.list_buckets()) <= 0:
        raise RuntimeError("Failed to verify credentials setup")

    return 0


if __name__ == "__main__":
    sys.exit(main())
