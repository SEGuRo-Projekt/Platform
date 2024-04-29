# SPDX-FileCopyrightText: 2023-2024 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import minio
import json
import logging
import tempfile

from seguro.commands.acl_syncer import model


def policies_from_acl(acl: model.AccessControlList) -> dict:
    return {
        name: policy_from_acl(acl, client)
        for name, client in acl.clients.items()
    }


def policy_from_acl(
    acl: model.AccessControlList, client: model.Client
) -> dict:
    roles_names: list[str] = []

    if client.roles is not None:
        roles_names += client.roles

    if client.groups is not None:
        for group_name in client.groups:
            try:
                group = acl.groups[group_name]
            except KeyError:
                raise Exception(
                    f"Unknown group '{group_name}'",
                )

            roles_names += group.roles

    statements: list[model.StoreStatement] = []

    for role_name in roles_names:
        try:
            role = acl.roles[role_name]
        except KeyError:
            raise Exception(f"Unknown role '{role_name}'")

        statements += role.store

    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": stm.effect.value,
                "Action": [f"s3:{action.value}" for action in stm.actions],
                "Resource": f"arn:aws:s3:::{stm.object}",
            }
            for stm in statements
        ],
    }


def reconcile(
    acl: model.AccessControlList,
    mca: minio.MinioAdmin,
    ignored_clients: set[str] = set(),
):
    existing_policies = json.loads(mca.policy_list())

    new_policies = policies_from_acl(acl)

    removed_policies = (
        frozenset(existing_policies.keys())
        - frozenset(new_policies.keys())
        - frozenset(ignored_clients)
    )

    # Remove empty policies
    removed_policies |= {
        name
        for name, p in new_policies.items()
        if len(p.get("Statement", [])) == 0 and name in existing_policies
    }

    for name in removed_policies:
        mca.policy_remove(name)
        logging.info("Removed store policy: %s", name)

    for name, policy in new_policies.items():
        if len(policy.get("Statement", [])) == 0:
            logging.warn(
                "Ignoring store policy without any statements: %s", name
            )
            continue

        with tempfile.NamedTemporaryFile("w+t") as tf:
            json.dump(policy, tf)
            tf.flush()

            mca.policy_add(name, tf.name)

        logging.info("Updated store policy: %s", name)
