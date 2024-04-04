"""
SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
SPDX-License-Identifier: Apache-2.0
"""

import functools
import logging
import json

import time

import seguro.common.store as store
from . import scheduler, compose


class Job(compose.Service):
    def __init__(
        self, name: str, spec: dict, scheduler: "scheduler.Scheduler"
    ):
        self.job_spec = spec
        self.logger = logging.getLogger(__name__)

        super().__init__(
            scheduler,
            name,
            spec.get("container", {}),
            spec.get("scale", 1),
            spec.get("recreate", False),
        )

        self.scheduler = scheduler
        self.watchers: list[store.Watcher] = []
        self.triggers = spec.get("triggers", [])

        for trigger in self.triggers:
            self._setup_trigger(trigger)

    def _setup_trigger(self, trigger: dict[str, str]):
        """Setup the trigger.

        Args:
          trigger: The trigger specification

        """

        typ = trigger.get("type")
        if typ in ["created", "removed", "modified"]:
            if typ == "created":
                event = store.Event.CREATED
            elif typ == "removed":
                event = store.Event.REMOVED
            elif typ == "modified":
                event = store.Event.CREATED | store.Event.REMOVED

            prefix = trigger.get("prefix", "/")

            cb = functools.partial(self._handle_trigger_event, trigger)

            watcher = self.scheduler.store.watch_async(prefix, cb, event)

            self.watchers.append(watcher)

        elif typ == "schedule":
            self._setup_schedule(trigger)

    def _handle_trigger_event(
        self, trigger: dict, _s: store.Client, evt: store.Event, obj: str
    ):
        """

        Args:
          trigger:
          _s:
          evt:
          obj:

        Returns:

        """
        triggered_by = {**trigger, "event": str(evt), "object": obj}
        info = {"triggered_by": triggered_by}

        self.start(info)

    def _setup_schedule(self, schedule: dict):
        """

        Args:
          schedule:

        """
        interval = schedule.get("interval", 1)

        job = self.scheduler.scheduler.every(interval)
        job.tag(self.name)

        if latest := schedule.get("interval_to"):
            job.to(latest)

        if at := schedule.get("at"):
            job.at(at)

        if until := schedule.get("until"):
            job.until(until)

        if unit := schedule.get("unit", "seconds"):
            job.unit = unit

            if job.unit == "weeks":
                if start_day := schedule.get("start_day", "monday"):
                    job.start_day = start_day

        info = {"triggered_by": schedule}

        job.do(self.start, info)

        self.logger.info(f"Started schedule {job}")

    def start(self, info: dict | None = None):
        """

        Args:
          info: dict | None:  (Default value = None)

        """
        full_info = {
            "name": self.name,
            "triggered_at": time.time(),
            **self.job_spec,
        }

        if info is not None:
            full_info.update(info)

        overlays = [
            {
                "services": {
                    self.name: {
                        "environment": {
                            "SEGURO_JOB_INFO": json.dumps(full_info)
                        }
                    }
                }
            }
        ]

        super().start(overlays)

        self.logger.info(f"Started job: {self.name}")

    def stop(self):
        self.scheduler.scheduler.clear(self.name)

        super().stop()

        for watcher in self.watchers:
            watcher.stop()
