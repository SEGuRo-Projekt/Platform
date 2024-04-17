#!/usr/bin/env python
# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import sys
import logging
import json
import os
import tempfile
import urllib3
from subprocess import check_call
from pprint import pformat

import minio
import minio.credentials

from seguro.common.config import (
    S3_HOST,
    S3_PORT,
    S3_BUCKET,
    TLS_CACERT,
    TLS_KEY,
    TLS_CERT,
)

POLICIES = {
    "admin": {
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Action": ["admin:*"]},
            {
                "Action": [
                    "s3:*",
                ],
                "Effect": "Allow",
                "Resource": [
                    f"arn:aws:s3:::{S3_BUCKET}",
                    f"arn:aws:s3:::{S3_BUCKET}/*",
                ],
            },
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
            mca.policy_add(name, tf.name)


def initialize_buckets(mc: minio.Minio):
    logging.info("Copy initial data to bucket")

    creds = mc._provider.retrieve()  # type: ignore
    url = mc._base_url

    check_call(
        [
            "mc",
            "--insecure",
            "config",
            "host",
            "add",
            "minio",
            f"https://{url.host}",
            creds.access_key,
            creds.secret_key,
        ]
    )

    # TODO


def main() -> int:
    logging.basicConfig(
        format="%(asctime)s.%(msecs)03d %(levelname)s %(name)s %(message)s",
        level=logging.INFO,
    )

    minio_user = os.environ.get("ADMIN_USERNAME", "")
    minio_pass = os.environ.get("ADMIN_PASSWORD", "")
    minio_endpoint = f"{S3_HOST}:{S3_PORT}"
    minio_url = f"https://{minio_endpoint}"

    http_client = urllib3.PoolManager(
        cert_reqs="CERT_REQUIRED", ca_certs=TLS_CACERT
    )
    creds_static = minio.credentials.StaticProvider(minio_user, minio_pass)
    mc = minio.Minio(
        minio_endpoint, credentials=creds_static, http_client=http_client
    )
    mca = minio.MinioAdmin(
        minio_endpoint, credentials=creds_static, http_client=http_client
    )

    logging.info("Server info: %s", pformat(json.loads(mca.info())))

    create_buckets(mc)
    initialize_buckets(mc)
    create_policies(mca)

    # Validate mTLS authentication
    creds_cert = minio.credentials.CertificateIdentityProvider(
        sts_endpoint=minio_url,
        cert_file=TLS_CERT,
        key_file=TLS_KEY,
        ca_certs=TLS_CACERT,
    )
    mc = minio.Minio(
        minio_endpoint, credentials=creds_cert, http_client=http_client
    )

    if len(mc.list_buckets()) <= 0:
        raise RuntimeError("Failed to verify credentials setup")

    return 0


if __name__ == "__main__":
    sys.exit(main())
