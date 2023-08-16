"""
SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
SPDX-License-Identifier: Apache-2.0
"""

import subprocess
import tempfile
import yaml
import json
import logging

from contextlib import contextmanager


class Service:
    def __init__(
        self, composer: "Composer", name: str, spec: dict, scale: int = 1
    ):
        self.composer = composer
        self.name = name
        self.service_spec = spec
        self.scale = scale

    def start(self):
        if self.composer.watch_proc is not None:
            self.composer.watch_proc.terminate()

        self.composer.compose(
            "up", "--scale", f"{self.name}={self.scale}", "--detach", self.name
        )

    def stop(self):
        self.composer.compose("down", self.name)


class Composer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.watch_proc = None

    @property
    def services(self):
        return []

    def compose(self, *args):
        with self.file() as file:
            file_fd = file.fileno()
            args = [
                "docker-compose",
                "--file",
                f"/proc/self/fd/{file_fd}",
                *args,
            ]
            self.logger.info(f"Running: {' '.join(args)}")
            subprocess.Popen(args, pass_fds=[file_fd])

    @property
    def spec(self) -> dict:
        return {
            "name": "scheduler",
            "services": {svc.name: svc.service_spec for svc in self.services},
        }

    @contextmanager
    def file(self):
        with tempfile.NamedTemporaryFile(mode="w+") as file:
            yaml.dump(self.spec, file)
            self.logger.info("Compose file:\n" + yaml.dump(self.spec))
            file.flush()
            yield file

    def _watch_events(self):
        with self.file() as file:
            args = ["docker-compose", "--file", file.name, "events", "--json"]
            self.logger.info(f"Running: {' '.join(args)}")

            self.watch_proc = subprocess.Popen(args, stdout=subprocess.PIPE)

            for line in self.watch_proc.stdout.readlines():
                output = json.loads(line)

                action = output.get("action")
                attrs = output.get("attributes")
                image = attrs.get("image")
                name = attrs.get("name")

                self.logger.info(f"Event {action} of {name}[{image}]")

    def run(self):
        while True:
            self._watch_events()

    def remove_orphans(self):
        self.compose("down", "--remove-orphans")
