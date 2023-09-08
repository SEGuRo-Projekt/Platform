"""
SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
SPDX-License-Identifier: Apache-2.0
"""

import copy
import json
import logging
import os
import subprocess
import tempfile
import yaml

from contextlib import contextmanager


class Service:
    def __init__(
        self,
        composer: "Composer",
        name: str,
        spec: dict,
        scale: int = 1,
        force_recreate: bool = False,
    ):
        self.composer = composer
        self.name = name
        self.service_spec = spec
        self.scale = scale
        self.force_recreate = force_recreate

    def start(self):
        if self.composer.watch_proc is not None:
            self.composer.watch_proc.terminate()

        args = ["up", "--detach", "--remove-orphans", "--quiet-pull"]

        if self.scale > 1:
            args += ["--scale", f"{self.name}={self.scale}"]

        if self.force_recreate:
            args += ["--force-recreate"]

        args += [self.name]

        self.composer.compose(*args)

    def stop(self):
        self.composer.compose("down", "--remove-orphans", self.name)

    @property
    def spec(self):
        spec = copy.deepcopy(self.service_spec)

        # Ensure that all env_file's are passed as absolute
        # paths, as docker-compose would otherwise resolve them
        # relatively to the docker-compose.yml which in our case
        # is /self/proc/fd/X. So env_file's would be resolved as
        # /self/proc/fd/some_env_file
        if env_files := spec.get("env_file"):
            if isinstance(env_files, str):
                env_files = [env_files]
            elif isinstance(env_files, list):
                env_files = [
                    f if os.path.isabs(f) else os.path.abspath(f)
                    for f in env_files
                ]

            spec["env_file"] = env_files

        return spec


class Composer:
    def __init__(self, name: str = "composer"):
        self.logger = logging.getLogger(__name__)
        self.watch_proc = None
        self.name = name

    @property
    def services(self):
        return []

    def compose(self, *args):
        with self.file() as file:
            file_fd = file.fileno()
            args = [
                "docker-compose",
                "--ansi",
                "never",
                "--progress",
                "plain",
                "--file",
                f"/proc/self/fd/{file_fd}",
                *args,
            ]
            self.logger.info(f"Running: {' '.join(args)}")
            subprocess.run(args, pass_fds=[file_fd])

    @property
    def spec(self) -> dict:
        return {
            "name": self.name,
            "services": {svc.name: svc.spec for svc in self.services},
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
