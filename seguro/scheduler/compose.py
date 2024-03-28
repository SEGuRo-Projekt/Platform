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
from typing import Optional
import yaml

from itertools import chain
from contextlib import contextmanager, ExitStack


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

    def start(self, overlays=[]):
        if self.composer.watch_proc is not None:
            self.composer.watch_proc.terminate()

        args = ["up", "--detach", "--quiet-pull"]

        if self.scale > 1:
            args += ["--scale", f"{self.name}={self.scale}"]

        if self.force_recreate:
            args += ["--force-recreate"]

        args += [self.name]

        self.composer.compose(*args, overlays=overlays)

    def stop(self):
        self.composer.compose("down", self.name)

    @property
    def spec(self):
        spec = copy.deepcopy(self.service_spec)

        # Ensure that all env_file's are passed as absolute
        # paths, as 'docker compose' would otherwise resolve them
        # relatively to the compose.yml which in our case
        # is /self/proc/fd/X. So env_file's would be resolved as
        # /self/proc/fd/some_env_file
        if env_files := spec.get("env_file"):
            if isinstance(env_files, str):
                env_files = [env_files]

            if isinstance(env_files, list):
                env_files = [
                    f if os.path.isabs(f) else os.path.abspath(f)
                    for f in env_files
                ]

                spec["env_file"] = env_files

        return spec


class Composer:
    def __init__(self, name: str = "composer"):
        self.logger = logging.getLogger(__name__)
        self.watch_proc: Optional[subprocess.Popen[bytes]] = None
        self.name = name

    @property
    def services(self):
        return []

    def compose(self, *args, overlays=[]):
        compose_file_contents = [self.spec] + overlays

        with ExitStack() as stack:
            compose_file_fds = [
                stack.enter_context(self._temp_file_fd(spec))
                for spec in compose_file_contents
            ]

            args = tuple(
                chain(
                    [
                        "docker",
                        "compose",
                        "--project-name",
                        self.name,
                        "--ansi",
                        "never",
                        "--progress",
                        "plain",
                    ],
                    chain.from_iterable(
                        [
                            ["--file", f"/proc/self/fd/{fd}"]
                            for fd in compose_file_fds
                        ]
                    ),
                    args,
                )
            )

            self.logger.info(f"Running: {' '.join(args)}")
            subprocess.run(args, pass_fds=compose_file_fds)

    @property
    def spec(self) -> dict:
        return {
            "services": {svc.name: svc.spec for svc in self.services},
            "networks": {
                "default": {"external": True, "name": "platform_default"}
            },
        }

    def run(self):
        while True:
            self._watch_events()

    def remove_orphans(self):
        self.compose("down", "--remove-orphans")

    def _watch_events(self):
        with self._temp_file_fd(self.spec) as fd:
            args = [
                "docker",
                "compose",
                "--file",
                f"/proc/self/fd/{fd}",
                "events",
                "--json",
            ]
            self.logger.info(f"Running: {' '.join(args)}")

            self.watch_proc = subprocess.Popen(
                args, stdout=subprocess.PIPE, pass_fds=[fd]
            )

            output = self.watch_proc.stdout
            if output is None:
                raise Exception("Missing output stream")

            for raw_line in output.readlines():
                line = json.loads(raw_line)

                action = line.get("action")
                attrs = line.get("attributes")
                image = attrs.get("image")
                name = attrs.get("name")

                self.logger.info(f"Event {action} of {name}[{image}]")

    @contextmanager
    def _temp_file_fd(self, contents: dict):
        with tempfile.NamedTemporaryFile(mode="w+") as file:
            yaml.dump(contents, file)
            self.logger.info("Compose file:\n" + yaml.dump(contents))
            file.flush()
            yield file.fileno()
