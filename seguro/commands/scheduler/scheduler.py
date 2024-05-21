# SPDX-FileCopyrightText: 2023-2024 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import docker
import schedule
import time
import logging
import os.path
import threading
import slugify
import yaml

import seguro.common.store as store
from seguro.commands.scheduler import job, compose, model


class Scheduler(compose.Composer):
    def __init__(
        self, docker_client: docker.DockerClient, store_client: store.Client
    ):
        super().__init__("scheduler")

        self.docker = docker_client
        self.store = store_client
        self.scheduler = schedule.Scheduler()
        self._stopflag = threading.Event()
        self.logger = logging.getLogger(__name__)

        self.logger.info("Scheduler starting")

        self.jobs: dict[str, job.Job] = {}

        self.watcher = self.store.watch_async(
            prefix="config/jobs/",
            cb=self._handler,
            events=store.Event.CREATED | store.Event.REMOVED,
            initial=True,
        )

    def _handler(self, _s: store.Client, event: store.Event, objname: str):
        """Callback for store events

        Args:
          _s: The store client
          event: the store event
          objname: The name of the store object

        """
        filename = os.path.basename(objname)
        name, ext = os.path.splitext(filename)

        if ext != ".yaml":
            self.logger.warn(f"Ignoring unsupported job file: {filename}")
            return

        job_name = slugify.slugify(name)

        if event == store.Event.CREATED:
            file = self.store.get_file_contents(objname)
            job_spec_dict = yaml.load(file, yaml.SafeLoader)

            try:
                job_spec = model.JobSpec(**job_spec_dict)
            except Exception as e:
                self.logger.error("Failed to parse job description:\n%s", e)
                return

            self._on_job_created(job_name, job_spec)
        elif event == store.Event.REMOVED:
            self._on_job_removed(job_name)

    def _on_job_created(self, name: str, spec: model.JobSpec):
        """Callback which get called when a job specification is
        added to the store.

        Args:
          name: Name of the job specification
          spec: The job specification

        """
        if name in self.jobs:
            self.jobs[name].stop()
            del self.jobs[name]

        self.jobs[name] = new_job = job.Job(name, spec, self)
        self.logger.info(f"Added new job: {name}")

        if triggers := new_job.job_spec.triggers:
            for trigger in triggers.values():

                if trigger.type != model.EventTriggerType.STARTUP:
                    continue

                new_job.start()
                break

        else:  # No triggers, configured -> start immediately
            new_job.start()

    def _on_job_removed(self, name: str):
        """Callback which get called when a job specification is removed
        from the store.

        Args:
          name: Name of the job specification

        """
        try:
            self.jobs[name].stop()
            del self.jobs[name]

            self.logger.info(f"Removed job: {name}")
        except KeyError:
            self.logger.warn(f"Attempted to remove unknown job: {name}")

    def run(self):
        while not self._stopflag.is_set():
            self.logger.debug("Run pending tasks")
            self.scheduler.run_pending()
            time.sleep(1)

    def stop(self):
        for j in self.jobs.values():
            j.stop()

        self._stopflag.set()
        self.watcher.stop()

    @property
    def services(self):
        return self.jobs.values()
