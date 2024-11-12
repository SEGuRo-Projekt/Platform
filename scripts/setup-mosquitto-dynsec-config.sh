#!/usr/bin/env bash
# shellcheck disable=SC2086

# SPDX-FileCopyrightText: 2023-2024 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

set -e

OPTS="-h ${MQTT_HOST:-localhost} -p ${MQTT_PORT:-8883} --cafile ${TLS_CACERT} --cert ${TLS_CERT} --key ${TLS_KEY}"

mosquitto_ctrl ${OPTS} dynsec addRoleACL admin publishClientSend '#' allow 5

mosquitto_ctrl ${OPTS} dynsec setDefaultACLAccess publishClientSend deny
mosquitto_ctrl ${OPTS} dynsec setDefaultACLAccess publishClientReceive deny
mosquitto_ctrl ${OPTS} dynsec setDefaultACLAccess subscribe deny
mosquitto_ctrl ${OPTS} dynsec setDefaultACLAccess unsubscribe deny
