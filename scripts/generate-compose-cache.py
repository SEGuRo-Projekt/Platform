#!/bin/env python
# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import os
import yaml
import json

OWNER = os.environ.get("GITHUB_REPOSITORY_OWNER", "SEGuRo-Projekt")
REF_NAME = os.environ.get("GITHUB_REF_NAME")

target: dict[str, dict] = {}
cache = {"target": target}

with open("compose.yaml") as f:
    compose = yaml.load(f, yaml.SafeLoader)

for name, service in compose.get("services", {}).items():
    if "image" in service:
        print(f"Skipping: {name}")
        continue  # Skip services with third-party images

    image = f"ghcr.io/{OWNER.lower()}/{name}"
    target[name] = {
        "cache-from": [f"type=registry,ref={image}:cache"],
        "cache-to": [f"type=registry,ref={image}:cache"],
        "output": ["type=docker"],
    }

with open("compose-cache.json", "wt") as f:
    json.dump(cache, f, indent=2)
