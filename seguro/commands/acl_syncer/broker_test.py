# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

from seguro.commands.acl_syncer import broker

cfg1 = broker.Config(
    clients={
        "c1": broker.Client(
            username="hans",
            groups=frozenset({broker.GroupEntry(groupname="g1")}),
            roles=frozenset({broker.RoleEntry(rolename="r1")}),
        )
    },
    groups={
        "g1": broker.Group(groupname="g1"),
        "g2": broker.Group(groupname="g2"),
    },
    roles={"r1": broker.Role(rolename="r1")},
)
cfg2 = broker.Config(
    clients={"c2": broker.Client(username="peter")}, groups={}, roles={}
)


def test_config_equal():
    cfg = cfg1.equal_to(cfg1)

    assert "c1" in cfg.clients


def test_config_unequal():
    cfg = cfg1.equal_to(cfg2)

    assert "c1" not in cfg.clients


def test_config_sub():
    cfg = cfg1.not_in(cfg1)

    assert len(cfg.clients) == 0
    assert len(cfg.groups) == 0
    assert len(cfg.roles) == 0


def test_config_and():
    pass


def test_config_part_of():
    cfg = cfg1.belonging_to({"c1"})

    assert "c1" in cfg.clients
    assert "g1" in cfg.groups
    assert "r1" in cfg.roles
    assert "g2" not in cfg.roles
