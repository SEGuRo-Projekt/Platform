# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

import functools
import logging
import datetime

from seguro.common import store
from seguro.commands.scheduler import scheduler, compose, model, compose_model


class Job(compose.Service):
    def __init__(
        self,
        name: str,
        job_spec: model.JobSpec,
        scheduler: "scheduler.Scheduler",
    ):
        self.job_spec: model.JobSpec = job_spec
        self.logger = logging.getLogger(__name__)

        super().__init__(
            scheduler,
            name,
            job_spec.container,
            job_spec.scale,
            job_spec.recreate,
            job_spec.build,
        )

        self.scheduler = scheduler
        self.watchers: list[store.Watcher] = []

        if triggers := self.job_spec.triggers:
            for id, trigger in triggers.items():
                self._setup_trigger(id, trigger)

    def _setup_trigger(self, id: str, trigger: model.Trigger):
        """Setup the trigger.

        Args:
          trigger: The trigger specification

        """

        if isinstance(trigger, model.StoreTrigger):
            if trigger.type == model.StoreTriggerType.CREATED:
                event = store.Event.CREATED
            elif trigger.type == model.StoreTriggerType.REMOVED:
                event = store.Event.REMOVED
            elif trigger.type == model.StoreTriggerType.MODIFIED:
                event = store.Event.CREATED | store.Event.REMOVED
            else:
                raise RuntimeError(f"Unknown trigger type: {trigger.type}")

            cb = functools.partial(self._handle_trigger_event, id)

            watcher = self.scheduler.store.watch_async(
                trigger.prefix, cb, event, trigger.initial
            )

            self.watchers.append(watcher)

        elif isinstance(trigger, model.ScheduleTrigger):
            self._setup_schedule(trigger)

    def _handle_trigger_event(
        self,
        trigger_id: str,
        _s: store.Client,
        evt: store.Event,
        obj: str,
    ):
        """

        Args:
          trigger:
          _s:
          evt:
          obj:

        Returns:

        """
        self.start(trigger_id=trigger_id, event=evt, object=obj)

    def _setup_schedule(self, schedule: model.ScheduleTrigger):
        """

        Args:
          schedule:

        """
        job = self.scheduler.scheduler.every(schedule.interval)
        job.tag(self.name)

        if latest := schedule.interval_to:
            job.to(latest)

        if at := schedule.at:
            job.at(at)

        if until := schedule.until:
            job.until(until)

        if unit := schedule.unit:
            job.unit = unit.value

            if unit == model.ScheduleUnit.WEEKS:
                if start_day := schedule.start_day:
                    job.start_day = start_day.value

        job.do(self.start, trigger=schedule)

        self.logger.info(f"Started schedule {job}")

    def start(  # type: ignore[override]
        self,
        trigger_id: str | None = None,
        event: store.Event | None = None,
        object: str | None = None,
    ):
        """

        Args:
          info: dict | None:  (Default value = None)

        """
        job_info = model.JobInfo(
            name=self.name,
            spec=self.job_spec,
        )

        if trigger_id is not None and self.job_spec.triggers is not None:
            trigger = self.job_spec.triggers[trigger_id]

            job_info.trigger = model.TriggerInfo(
                id=trigger_id,
                type=trigger.type,
                time=datetime.datetime.now(),
                event=event,
                object=object,
            )

        overlay = compose_model.ComposeSpecification(
            services={
                self.name: compose_model.Service(
                    environment={
                        "SEGURO_JOB_INFO": job_info.json(exclude_none=True),
                        "S3_HOST": "minio",
                        "MQTT_HOST": "mosquitto",
                        "TLS_CACERT": "/certs/ca.crt",
                        "TLS_CERT": "/certs/clients/admin.crt",
                        "TLS_KEY": "/keys/clients/admin.key",
                    },  # type: ignore
                    env_file=compose_model.EnvFile(root=[".env"]),
                    volumes=[
                        compose_model.Volumes(
                            type="volume",
                            source="key_clients",
                            target="/keys/clients",
                            read_only=True,
                        ),
                        compose_model.Volumes(
                            type="volume",
                            source="certs",
                            target="/certs",
                            read_only=True,
                        ),
                    ],
                )
            },
            volumes={
                vol: compose_model.Volume(
                    name=f"platform_{vol}", external=compose_model.External()
                )
                for vol in ["key_clients", "certs"]
            },
        )

        super().start([overlay])

        self.logger.info(f"Started job: {self.name}")

    def stop(self, down: bool = False):
        self.scheduler.scheduler.clear(self.name)

        if down:
            super().stop()

        for watcher in self.watchers:
            watcher.stop()
