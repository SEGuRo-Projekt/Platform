# SPDX-FileCopyrightText: 2023-2024 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

# References:
# - https://mosquitto.org/documentation/dynamic-security/
# - https://github.com/eclipse/mosquitto/blob/master/plugins/dynamic-security/README.md # noqa


import json
import queue
import dataclasses
import logging
import pydantic
from enum import Enum
from itertools import chain

from seguro.common import broker as cbroker
from seguro.commands.acl_syncer import model


class BaseModel(pydantic.BaseModel, frozen=True):
    def dump(self):
        return self.model_dump(mode="json", exclude_none=True)


class ACLType(Enum):
    PUBLISH_CLIENT_SEND = "publishClientSend"
    PUBLISH_CLIENT_RECEIVE = "publishClientReceive"
    SUBSCRIBE_LITERAL = "subscribeLiteral"
    SUBSCRIBE_PATTERN = "subscribePattern"
    UNSUBSCRIBE_LITERAL = "unsubscribeLiteral"
    UNSUBSCRIBE_PATTERN = "unsubscribePattern"

    @classmethod
    def from_broker_action(cls, act: model.BrokerAction) -> list["ACLType"]:
        if act == model.BrokerAction.PUBLISH:
            return [cls.PUBLISH_CLIENT_SEND]
        elif act == model.BrokerAction.SUBSCRIBE:
            return [
                cls.SUBSCRIBE_PATTERN,
                cls.UNSUBSCRIBE_PATTERN,
                cls.PUBLISH_CLIENT_RECEIVE,
            ]
        else:
            raise RuntimeError(f"Unsupported broker action: {act}")


class GroupEntry(BaseModel, frozen=True):
    groupname: str
    priority: int = -1


class RoleEntry(BaseModel, frozen=True):
    rolename: str
    priority: int = -1


class ACL(BaseModel, frozen=True):
    acltype: ACLType
    topic: str
    priority: int = -1
    allow: bool = True


class Group(BaseModel, frozen=True):
    groupname: str
    roles: frozenset[RoleEntry] = frozenset()

    @property
    def name(self) -> str:
        return self.groupname


class Role(BaseModel, frozen=True):
    rolename: str
    textname: str | None = None
    textdescription: str | None = None
    acls: frozenset[ACL] = frozenset()

    @property
    def name(self) -> str:
        return self.rolename


class Client(BaseModel, frozen=True):
    username: str
    password: str | None = None
    clientid: str | None = None
    textname: str | None = None
    textdescription: str | None = None
    groups: frozenset[GroupEntry] = frozenset()
    roles: frozenset[RoleEntry] = frozenset()

    @property
    def name(self) -> str:
        return self.username


@dataclasses.dataclass
class Config:
    clients: dict[str, Client]
    groups: dict[str, Group]
    roles: dict[str, Role]

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

    def not_in(self, other: "Config") -> "Config":
        return Config(
            clients={
                k: v
                for k, v in self.clients.items()
                if k not in other.clients.keys()
            },
            groups={
                k: v
                for k, v in self.groups.items()
                if k not in other.groups.keys()
            },
            roles={
                k: v
                for k, v in self.roles.items()
                if k not in other.roles.keys()
            },
        )

    def also_in(self, other: "Config") -> "Config":
        return Config(
            clients={
                k: v
                for k, v in self.clients.items()
                if k in other.clients.keys() and k in self.clients.keys()
            },
            groups={
                k: v
                for k, v in self.groups.items()
                if k in other.groups.keys() and k in self.groups.keys()
            },
            roles={
                k: v
                for k, v in self.roles.items()
                if k in other.roles.keys() and k in self.roles.keys()
            },
        )

    def belonging_to(self, client_names: set[str] = set()) -> "Config":
        clients = {k: v for k, v in self.clients.items() if k in client_names}
        groups: dict[str, Group] = {}
        roles: dict[str, Role] = {}

        for client in clients.values():
            client_roles = set(client.roles)

            for g in client.groups:
                if not (group_name := g.groupname):
                    continue

                if not (group := self.groups.get(group_name)):
                    continue

                client_roles |= set(group.roles)

                groups[group_name] = group

            for c in client_roles:
                if not (role_name := c.rolename):
                    continue

                if not (role := self.roles.get(role_name)):
                    continue

                roles[role_name] = role

        return Config(clients, groups, roles)

    def equal_to(self, other: "Config") -> "Config":
        return Config(
            clients={
                k: v for k, v in (self.clients.items() & other.clients.items())
            },
            groups={
                k: v for k, v in (self.groups.items() & other.groups.items())
            },
            roles={
                k: v for k, v in (self.roles.items() & other.roles.items())
            },
        )

    @classmethod
    def from_acl(cls, acl: model.AccessControlList) -> "Config":
        return cls(
            clients={
                name: Client(
                    username=name,
                    groups=frozenset(
                        {
                            GroupEntry(groupname=group)
                            for group in client.groups
                        }
                    ),
                    roles=frozenset(
                        {RoleEntry(rolename=role) for role in client.roles}
                    ),
                )
                for name, client in acl.clients.items()
            },
            groups={
                name: Group(
                    groupname=name,
                    roles=frozenset(
                        {RoleEntry(rolename=role) for role in group.roles}
                    ),
                )
                for name, group in acl.groups.items()
            },
            roles={
                name: Role(
                    rolename=name,
                    acls=frozenset(
                        chain.from_iterable(
                            chain.from_iterable(
                                [
                                    (
                                        (
                                            ACL(
                                                acltype=acl_type,
                                                topic=acl.topic,
                                                allow=acl.effect
                                                == model.Effect.ALLOW,
                                            )
                                            for acl_type in ACLType.from_broker_action(  # noqa
                                                act
                                            )
                                        )
                                        for act in acl.actions
                                    )
                                    for acl in role.broker
                                ]
                            )
                        )
                    ),
                )
                for name, role in acl.roles.items()
            },
        )


class Command:
    def __init__(self, cmd: str, **attrs):
        self.command = cmd
        self.attrs = attrs

    def to_dict(self):
        return {"command": self.command, **self.attrs}

    @classmethod
    def set_default_access(self, acls: dict[ACLType, bool]):
        return {
            "command": "setDefaultACLAccess",
            "acls": [
                {"acltype": k.value, "allow": v} for k, v in acls.items()
            ],
        }

    @classmethod
    def create_client(cls, client: Client):
        return cls("createClient", **client.dump())

    @classmethod
    def modify_client(cls, client: Client):
        return cls("modifyClient", **client.dump())

    @classmethod
    def create_group(cls, group: Group):
        return cls("createGroup", **group.dump())

    @classmethod
    def modify_group(cls, group: Group):
        return cls("modifyGroup", **group.dump())

    @classmethod
    def create_role(cls, role: Role):
        return cls("createRole", **role.dump())

    @classmethod
    def modify_role(cls, role: Role):
        return cls("modifyRole", **role.dump())

    @classmethod
    def delete_client(cls, name: str):
        return cls("deleteClient", username=name)

    @classmethod
    def delete_group(cls, name: str):
        return cls("deleteGroup", groupname=name)

    @classmethod
    def delete_role(cls, name: str):
        return cls("deleteRole", rolename=name)

    @classmethod
    def list_clients(
        cls, verbose: bool = True, count: int = -1, offset: int = 0
    ):
        return cls("listClients", verbose=verbose, count=count, offset=offset)

    @classmethod
    def list_groups(
        cls, verbose: bool = True, count: int = -1, offset: int = 0
    ):
        return cls("listGroups", verbose=verbose, count=count, offset=offset)

    @classmethod
    def list_roles(
        cls, verbose: bool = True, count: int = -1, offset: int = 0
    ):
        return cls("listRoles", verbose=verbose, count=count, offset=offset)


class Plugin:
    def __init__(self, b: cbroker.Client):
        self.client = b
        self.queue: queue.Queue[cbroker.Message] = queue.Queue()
        self.client.subscribe(
            "$CONTROL/dynamic-security/v1/response", self._on_response
        )

    def get_current_config(self) -> Config:
        resps = self.execute(
            [
                Command.list_clients(),
                Command.list_groups(),
                Command.list_roles(),
            ]
        )

        for resp in resps:
            cmd = resp["command"]
            data = resp["data"]

            if cmd == "listClients":
                clients = [Client(**client) for client in data["clients"]]
            elif cmd == "listGroups":
                groups = [Group(**group) for group in data["groups"]]
            elif cmd == "listRoles":
                roles = [Role(**role) for role in data["roles"]]

        return Config(
            clients={client.name: client for client in clients},
            groups={group.name: group for group in groups},
            roles={role.name: role for role in roles},
        )

    def create(self, cfg: Config) -> list[Command]:
        cmds = []

        for name, role in cfg.roles.items():
            logging.info("Create broker role: %s", name)
            cmds.append(Command.create_role(role))
        for name, group in cfg.groups.items():
            logging.info("Create broker group: %s", name)
            cmds.append(Command.create_group(group))
        for name, client in cfg.clients.items():
            logging.info("Create broker client: %s", name)
            cmds.append(Command.create_client(client))

        return cmds

    def modify(self, cfg: Config) -> list[Command]:
        cmds = []

        for name, role in cfg.roles.items():
            logging.info("Modify broker role: %s", name)
            cmds.append(Command.modify_role(role))
        for name, group in cfg.groups.items():
            logging.info("Modify broker group: %s", name)
            cmds.append(Command.modify_group(group))
        for name, client in cfg.clients.items():
            logging.info("Modify broker client: %s", name)
            cmds.append(Command.modify_client(client))

        return cmds

    def delete(self, cfg: Config) -> list[Command]:
        cmds = []

        for name in cfg.clients:
            logging.info("Delete broker client: %s", name)
            cmds.append(Command.delete_client(name))
        for name in cfg.groups:
            logging.info("Delete broker group: %s", name)
            cmds.append(Command.delete_group(name))
        for name in cfg.roles:
            logging.info("Delete broker role: %s", name)
            cmds.append(Command.delete_role(name))

        return cmds

    def execute(self, cmds: list[Command], timeout: float = 2.0):
        cmd_payload = json.dumps({"commands": [cmd.to_dict() for cmd in cmds]})
        self.client.publish("$CONTROL/dynamic-security/v1", cmd_payload)

        msg = self.queue.get(True, timeout=timeout)

        resp = json.loads(msg.payload)

        return resp.get("responses", [])

    def _on_response(self, _: cbroker.Client, msg: cbroker.Message):
        self.queue.put(msg)


def reconcile(
    acl: model.AccessControlList,
    b: cbroker.Client,
    ignored_clients: set[str] = set(),
):
    dsp = Plugin(b)

    new = Config.from_acl(acl)
    current = dsp.get_current_config()

    # Remove system clients, groups and roles from changeset
    new = new.not_in(new.belonging_to(ignored_clients))
    current = current.not_in(current.belonging_to(ignored_clients))

    logging.info("New broker ACL: %s", new)
    logging.info("Current broker ACL: %s", current)

    unchanged = new.equal_to(current)
    modify = new.also_in(current).not_in(unchanged)
    create = new.not_in(current)
    delete = current.not_in(new)

    cmds = dsp.create(create) + dsp.modify(modify) + dsp.delete(delete)

    if len(cmds) > 0:
        dsp.execute(cmds)

        logging.info("Updated config: %s", dsp.get_current_config())
