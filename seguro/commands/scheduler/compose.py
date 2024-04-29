# SPDX-FileCopyrightText: 2023-2024 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import os
import subprocess
import tempfile
import yaml
from typing import Any

from itertools import chain
from contextlib import contextmanager, ExitStack

from seguro.commands.scheduler import compose_model


class Service:
    def __init__(
        self,
        composer: "Composer",
        name: str,
        service_spec: compose_model.Service,
        scale: int = 1,
        force_recreate: bool = False,
        build: bool = False,
    ):
        self.composer = composer
        self.name = name
        self.service_spec = service_spec
        self.scale = scale
        self.force_recreate = force_recreate
        self.build = build

    def start(self, overlays: list[compose_model.ComposeSpecification] = []):
        """

        Args:
          overlays:  (Default value = [])

        """
        if self.composer.watch_proc is not None:
            self.composer.watch_proc.terminate()

        args = ["up", "--detach", "--quiet-pull"]

        if self.scale > 1:
            args += ["--scale", f"{self.name}={self.scale}"]

        if self.force_recreate:
            args += ["--force-recreate"]

        if self.build:
            args += ["--build"]

        args += [self.name]

        self.composer.compose(*args, overlays=overlays)

    def stop(self):
        self.composer.compose("down", self.name)

    @property
    def spec(self):
        return self.service_spec


class Composer:
    def __init__(self, name: str = "composer"):
        self.logger = logging.getLogger(__name__)
        self.watch_proc: subprocess.Popen[bytes] | None = None
        self.name = name

    @staticmethod
    def _fix_spec(spec: compose_model.ComposeSpecification) -> dict:
        spec = spec.copy()

        def make_abs(f: str) -> str:
            return f if os.path.isabs(f) else os.path.abspath(f)

        spec_dict = spec.dict(exclude_unset=True)

        for name, service in spec_dict.get("services", {}).items():
            # Ensure that all env_file's are passed as absolute
            # paths, as 'docker compose' would otherwise resolve them
            # relatively to the compose.yml which in our case
            # is /self/proc/fd/X. So env_file's would be resolved as
            # /self/proc/fd/some_env_file

            if env_file := service.get("env_file"):
                if isinstance(env_file, str):
                    service["env_file"] = make_abs(env_file)
                elif isinstance(env_file, list):
                    for i, env_file_entry in enumerate(env_file):
                        if isinstance(env_file_entry, str):
                            env_file[i] = make_abs(env_file_entry)

        for name, network in spec_dict.get("networks", {}).items():
            if isinstance(network, dict):
                if external := network.get("external"):
                    network["name"] = external.get("name", "default")
                    network["external"] = True

        return spec_dict

    @property
    def services(self):
        return []

    def compose(
        self, *args, overlays: list[compose_model.ComposeSpecification] = []
    ):
        """

        Args:
          *args:
          overlays:  (Default value = [])

        Returns:

        """
        specs = [self.spec] + overlays
        specs_dict = [Composer._fix_spec(spec) for spec in specs]

        for i, spec_dict in enumerate(specs_dict):
            self.logger.debug(
                "Compose spec %d of %d:\n%s",
                i + 1,
                len(specs_dict),
                yaml.dump(spec_dict),
            )

        with ExitStack() as stack:
            compose_file_fds = [
                stack.enter_context(self._temp_file_fd(spec))
                for spec in specs_dict
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
    def spec(self) -> compose_model.ComposeSpecification:
        return compose_model.ComposeSpecification(
            services={svc.name: svc.spec for svc in self.services},
            networks={
                "default": compose_model.Network(
                    external=compose_model.External(name="platform_default")
                )
            },
        )

    def run(self):
        while True:
            self._watch_events()

    def remove_orphans(self):
        self.compose("down", "--remove-orphans")

    def _watch_events(self):
        with self._temp_file_fd(self.spec.dict()) as fd:
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
    def _temp_file_fd(self, contents: dict[str, Any]):
        """

        Args:
          contents:

        Yields:
          A file descriptor to a temporary file

        """
        with tempfile.NamedTemporaryFile(mode="w+") as file:
            yaml.dump(contents, file)
            file.flush()
            yield file.fileno()
