# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel
from enum import Enum
from typing import Any

Condition = dict[str, dict[str, str]]


def _unique(items: list[Any]) -> list[Any]:
    new_list = []
    for item in items:
        if item in new_list:
            continue
        new_list.append(item)
    return new_list


class Effect(Enum):
    ALLOW = "Allow"
    DENY = "Deny"


class BrokerAction(Enum):
    PUBLISH = "Publish"
    SUBSCRIBE = "Subscribe"


class StoreAction(Enum):
    ANY = "*"
    GET_OBJECT = "GetObject"
    DELETE_OBJECT = "DeleteObject"
    PUT_OBJECT = "PutObject"
    LIST_OJECTS = "ListObjects"


class StoreStatement(BaseModel):
    effect: Effect = Effect.ALLOW
    actions: set[StoreAction] = {StoreAction.ANY}
    object: str
    condition: Condition = {}


class BrokerStatement(BaseModel):
    effect: Effect = Effect.ALLOW
    actions: set[BrokerAction] = {
        BrokerAction.PUBLISH,
        BrokerAction.SUBSCRIBE,
    }
    topic: str
    priority: int = -1


class Role(BaseModel):
    broker: list[BrokerStatement] = []
    store: list[StoreStatement] = []

    def update(self, other: "Role") -> "Role":
        return Role(
            broker=_unique(self.broker + other.broker),
            store=_unique(self.store + other.store),
        )


class Group(BaseModel):
    roles: list[str]

    def update(self, other: "Group") -> "Group":
        return Group(
            roles=_unique(self.roles + other.roles),
        )


class Client(BaseModel):
    groups: list[str] = []
    roles: list[str] = []

    def update(self, other: "Client") -> "Client":
        return Client(
            groups=_unique(self.groups + other.groups),
            roles=_unique(self.roles + other.roles),
        )


class AccessControlList(BaseModel):
    groups: dict[str, Group] = {}
    roles: dict[str, Role] = {}
    clients: dict[str, Client] = {}

    def __str__(self):
        client_names = ", ".join(sorted(self.clients.keys()))
        group_names = ", ".join(sorted(self.groups.keys()))
        role_names = ", ".join(sorted(self.roles.keys()))

        return " ".join(
            [
                f"clients=[{client_names}]",
                f"groups=[{group_names}]",
                f"roles=[{role_names}]",
            ]
        )

    def update(self, other: "AccessControlList") -> "AccessControlList":
        new_clients = self.clients.copy()
        new_groups = self.groups.copy()
        new_roles = self.roles.copy()

        for name, other_client in other.clients.items():
            if new_client := new_clients.get(name):
                new_clients[name] = new_client.update(other_client)
            else:
                new_clients[name] = other_client

        for name, other_group in other.groups.items():
            if new_group := new_groups.get(name):
                new_groups[name] = new_group.update(other_group)
            else:
                new_groups[name] = other_group

        for name, other_role in other.roles.items():
            if new_role := new_roles.get(name):
                new_roles[name] = new_role.update(other_role)
            else:
                new_roles[name] = other_role

        return AccessControlList(
            clients=new_clients, groups=new_groups, roles=new_roles
        )
