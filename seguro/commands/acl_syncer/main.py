# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

# References:
# - https://min.io/docs/minio/linux/administration/identity-access-management/policy-based-access-control.html#overview # noqa
# - https://github.com/minio/minio/blob/master/docs/sts/tls.md?ref=blog.min.io#assumerolewithcertificate # noqa

import os
import sys
import yaml
import urllib3
import pathlib
import logging

import minio

from seguro.commands.acl_syncer import broker, store, model
from seguro.common import broker as cbroker, store as cstore, config

IGNORED_CLIENTS = {
    "consoleAdmin",
    "diagnostics",
    "readwrite",
    "readonly",
    "writeonly",
    "admin",
}

ACL_PREFIX = "config/acls/"


def main() -> int:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s.%(msecs)03d %(levelname)s %(name)s %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("urllib3").setLevel(logging.INFO)

    s = cstore.Client()
    b = cbroker.Client()

    http_client = urllib3.PoolManager(
        cert_reqs="CERT_REQUIRED", ca_certs=config.TLS_CACERT
    )

    minio_endpoint = f"{config.S3_HOST}:{config.S3_PORT}"
    minio_user = os.environ.get("ADMIN_USERNAME", "")
    minio_pass = os.environ.get("ADMIN_PASSWORD", "")
    creds = minio.credentials.StaticProvider(minio_user, minio_pass)
    mca = minio.MinioAdmin(
        minio_endpoint, credentials=creds, http_client=http_client
    )

    acl_objs = s.client.list_objects(
        s.bucket, prefix=ACL_PREFIX, recursive=True
    )

    acl_all = model.AccessControlList()

    for acl_obj in acl_objs:
        acl_path = pathlib.Path(acl_obj.object_name)
        acl_name = acl_path.stem

        resp = s.get_file_contents(acl_path.as_posix())

        acl_dict = yaml.load(resp, yaml.SafeLoader)
        acl = model.AccessControlList(**acl_dict)
        acl = acl.prefix(acl_name + "-")

        logging.info("Load ACL: %s=%s", acl_name, acl)

        acl_all = acl_all.update(acl)

    broker.reconcile(acl_all, b, IGNORED_CLIENTS)
    store.reconcile(acl_all, mca, IGNORED_CLIENTS)

    return 0


if __name__ == "__main__":
    sys.exit(main())
