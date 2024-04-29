#!/usr/bin/env bash
# shellcheck disable=SC2086

# SPDX-FileCopyrightText: 2023-2024 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

set -e

# TODO: Remove once acl-syncer is ready
OPTS="-h ${MQTT_HOST:-localhost} -p ${MQTT_PORT:-8883} --cafile ${TLS_CACERT} --cert ${TLS_CERT} --key ${TLS_KEY}"

mosquitto_ctrl ${OPTS} dynsec setDefaultACLAccess publishClientSend allow
mosquitto_ctrl ${OPTS} dynsec setDefaultACLAccess publishClientReceive allow
mosquitto_ctrl ${OPTS} dynsec setDefaultACLAccess subscribe allow
mosquitto_ctrl ${OPTS} dynsec setDefaultACLAccess unsubscribe allow
