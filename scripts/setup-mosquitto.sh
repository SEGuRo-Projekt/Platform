#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2023-2024 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

set -e

rm -f /mosquitto/data/dynsec.json

mosquitto_ctrl dynsec init /mosquitto/data/dynsec.json "${ADMIN_USERNAME}" "${ADMIN_PASSWORD}"

mosquitto_ctrl ${OPTS} dynsec setDefaultACLAccess publishClientSend deny
mosquitto_ctrl ${OPTS} dynsec setDefaultACLAccess publishClientReceive deny
mosquitto_ctrl ${OPTS} dynsec setDefaultACLAccess subscribe deny
mosquitto_ctrl ${OPTS} dynsec setDefaultACLAccess unsubscribe deny

mosquitto_ctrl ${OPTS} dynsec addRoleACL admin publishClientSend '#' allow 5