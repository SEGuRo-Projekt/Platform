"""
SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
SPDX-License-Identifier: Apache-2.0
"""

import docker
import schedule
import time
import logging
import os.path
import threading
import slugify
import yaml

from typing import Dict

import seguro.common.store as store
from . import job, compose


class Scheduler(compose.Composer):
    def __init__(
        self, docker_client: docker.DockerClient, store_client: store.Client
    ):
        super().__init__()

        self.docker = docker_client
        self.store = store_client
        self.scheduler = schedule.Scheduler()
        self._stopflag = threading.Event()
        self.logger = logging.getLogger(__name__)

        self.logger.info("Scheduler starting")

        self.jobs: Dict[str, job.Job] = {}

        self.watcher = self.store.watch_async(
            "config/jobs/",
            self._handler,
            store.Event.CREATED | store.Event.REMOVED,
        )

        self._get_jobs_from_store()

    def _get_jobs_from_store(self):
        objs = self.store.client.list_objects("seguro", "config/jobs/")

        for obj in objs:
            self._handler(store.Event.CREATED, obj.object_name)

    def _handler(self, event: store.Event, objname: str):
        filename = os.path.basename(objname)
        name, ext = os.path.splitext(filename)

        if ext != ".yaml":
            self.logger.warn(f"Ignoring unsupported job file: {filename}")
            return

        job_name = slugify.slugify(name)

        if event == store.Event.CREATED:
            file = self.store.get_file_contents(objname)
            spec = yaml.load(file, yaml.SafeLoader)
            self._on_job_created(job_name, spec)
        elif event == store.Event.REMOVED:
            self._on_job_removed(job_name)

    def _on_job_created(self, name: str, spec: dict):
        if name in self.jobs:
            self.jobs[name].stop()
            del self.jobs[name]

        self.jobs[name] = job.Job(name, spec, self)

        self.logger.info(f"Added new job: {name}")

    def _on_job_removed(self, name: str):
        try:
            self.jobs[name].stop()
            del self.jobs[name]

            self.logger.info(f"Removed job: {name}")
        except KeyError:
            self.logger.warn(f"Attempted to remove unknown job: {name}")

    def run(self):
        # thd = threading.Thread(target=super().run)
        # thd.start()

        while not self._stopflag.is_set():
            self.logger.debug("Run pending tasks")
            self.scheduler.run_pending()
            time.sleep(1)

        # thd.join()

    def stop(self):
        self._stopflag.set()
        self.watcher.stop()

    @property
    def services(self):
        return self.jobs.values()
