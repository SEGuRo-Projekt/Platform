#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2023-2024 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

read -p "Are you sure you want to reset the platform? Warning: all data will be erased! (y/n) " -n 1 -r
if [[ $REPLY =~ ^[Yy]$ ]]; then
	for PROJECT in scheduler platform; do
		docker compose \
			--project-name "${PROJECT}" \
			down \
				--remove-orphans \
				--volumes 2>&1 |  \
		grep -v "Warning: No resource found to remove"
	done
fi
