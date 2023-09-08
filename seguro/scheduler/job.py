"""
SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
SPDX-License-Identifier: Apache-2.0
"""

import logging

from typing import Dict

import seguro.common.store as store
from . import scheduler, compose


class Job(compose.Service):
    def __init__(
        self, name: str, spec: dict, scheduler: "scheduler.Scheduler"
    ):
        self.spec = spec
        self.logger = logging.getLogger(__name__)

        super().__init__(
            scheduler,
            name,
            self.spec.get("container", {}),
            self.spec.get("scale", 1),
            self.spec.get("recreate", False),
        )

        self.scheduler = scheduler
        self.watchers = []
        self.triggers = self.spec.get("triggers", [])

        for trigger in self.triggers:
            self._setup_trigger(trigger)

    def _setup_trigger(self, trigger: dict):
        typ: str = trigger.get("type")
        if typ in ["created", "removed"]:
            event = store.Event[typ.upper()]
            prefix = trigger.get("prefix", "/")

            watcher = self.scheduler.store.watch_async(
                prefix, self._handle_trigger_event, event
            )

            self.watchers.append(watcher)

        elif typ == "schedule":
            self._setup_schedule(trigger)

    def _handle_trigger_event(self, typ: store.Event, filename: str):
        self.start()

    def _setup_schedule(self, schedule: Dict):
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

        job.do(self.start)

        self.logger.info(f"Started schedule {job}")

    def start(self):
        super().start()
        self.logger.info(f"Started job: {self.name}")

    def stop(self):
        self.scheduler.scheduler.clear(self.name)

        super().stop()

        for watcher in self.watchers:
            watcher.stop()
