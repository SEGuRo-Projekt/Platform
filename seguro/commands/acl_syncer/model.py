# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel
from enum import Enum

Condition = dict[str, dict[str, str]]


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
    actions: list[StoreAction] = [StoreAction.ANY]
    object: str
    condition: Condition = {}


class BrokerStatement(BaseModel):
    effect: Effect = Effect.ALLOW
    actions: list[BrokerAction] = [
        BrokerAction.PUBLISH,
        BrokerAction.SUBSCRIBE,
    ]
    topic: str
    priority: int = -1


class Role(BaseModel):
    broker: list[BrokerStatement] = []
    store: list[StoreStatement] = []


class Group(BaseModel):
    roles: list[str]

    def prefix(self, pfx: str) -> "Group":
        return Group(
            roles=[pfx + v for v in self.roles],
        )


class Client(BaseModel):
    groups: list[str] = []
    roles: list[str] = []

    def prefix(self, pfx: str) -> "Client":
        return Client(
            groups=[pfx + v for v in self.groups],
            roles=[pfx + v for v in self.roles],
        )


class AccessControlList(BaseModel):
    groups: dict[str, Group] = {}
    roles: dict[str, Role] = {}
    clients: dict[str, Client] = {}

    def __str__(self):
        client_names = " ".join(self.clients.keys())
        group_names = " ".join(self.groups.keys())
        role_names = " ".join(self.roles.keys())

        return (
            f"<AccessControlList clients=({client_names}) "
            + f"groups=({group_names}) roles=({role_names})>"
        )

    def prefix(self, pfx: str) -> "AccessControlList":
        return AccessControlList(
            clients={pfx + k: v.prefix(pfx) for k, v in self.clients.items()},
            groups={pfx + k: v.prefix(pfx) for k, v in self.groups.items()},
            roles={pfx + k: v for k, v in self.roles.items()},
        )

    def update(self, other: "AccessControlList") -> "AccessControlList":
        return AccessControlList(
            clients={**self.clients, **other.clients},
            groups={**self.groups, **other.groups},
            roles={**self.roles, **other.roles},
        )
