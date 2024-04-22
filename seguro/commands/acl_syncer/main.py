# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

# References:
# - https://min.io/docs/minio/linux/administration/identity-access-management/policy-based-access-control.html#overview # noqa
# - https://github.com/minio/minio/blob/master/docs/sts/tls.md?ref=blog.min.io#assumerolewithcertificate # noqa

import sys
import yaml
import urllib3
import pathlib
import logging

import minio
import pydantic

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


def merge_acls(acls: list[model.AccessControlList]) -> model.AccessControlList:
    acl_all = model.AccessControlList()

    for acl in acls:
        acl_all = acl_all.update(acl)

    return acl_all


def get_acls(s: cstore.Client):
    acls: list[model.AccessControlList] = []

    objs = s.client.list_objects(s.bucket, prefix=ACL_PREFIX, recursive=True)

    # Apply ACLs in the order based on their object name
    objs = sorted(objs, key=lambda obj: obj.object_name)

    for obj in objs:
        acl_path = pathlib.Path(obj.object_name)
        acl_name = acl_path.stem

        resp = s.get_file_contents(acl_path.as_posix())

        acl_dict = yaml.load(resp, yaml.SafeLoader)

        try:
            acl = model.AccessControlList(**acl_dict)
        except pydantic.ValidationError as e:
            logging.error("Ignoring malformed ACL: '%s'\n%s", acl_name, e)
            continue

        logging.info("Loaded ACL '%s' with %s", acl_name, acl)

        acls.append(acl)

    return acls


def main() -> int:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s.%(msecs)03d %(levelname)s %(name)s %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("urllib3").setLevel(logging.INFO)
    logging.getLogger("seguro.common.broker").setLevel(logging.INFO)

    s = cstore.Client()
    b = cbroker.Client()

    http_client = urllib3.PoolManager(
        cert_reqs="CERT_REQUIRED", ca_certs=config.TLS_CACERT
    )

    minio_endpoint = f"{config.S3_HOST}:{config.S3_PORT}"
    creds = minio.credentials.CertificateIdentityProvider(
        sts_endpoint=f"https://{minio_endpoint}",
        cert_file=config.TLS_CERT,
        key_file=config.TLS_KEY,
        ca_certs=config.TLS_CACERT,
    )
    mca = minio.MinioAdmin(
        minio_endpoint, credentials=creds, http_client=http_client
    )

    acls = get_acls(s)
    acl = merge_acls(acls)

    rc = 0

    try:
        broker.reconcile(acl, b, IGNORED_CLIENTS)
    except Exception as e:
        rc |= 1
        logging.error("Failed to reconcile broker: %s", e)

    try:
        store.reconcile(acl, mca, IGNORED_CLIENTS)
    except Exception as e:
        rc |= 2
        logging.error("Failed to reconcile store: %s", e)

    return rc


if __name__ == "__main__":
    sys.exit(main())
