# SPDX-FileCopyrightText: 2023-2024 Steffen Vogel, OPAL-RT Germany GmbH
# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel, Field
from enum import Enum
import datetime

from seguro.common import store
from seguro.commands.scheduler.compose_model import Service


class StoreTriggerType(Enum):
    CREATED = "created"
    REMOVED = "removed"
    MODIFIED = "modified"


class ScheduleTriggerType(Enum):
    SCHEDULE = "schedule"


class EventTriggerType(Enum):
    STARTUP = "startup"
    SHUTDOWN = "shutdown"


TriggerType = StoreTriggerType | ScheduleTriggerType | EventTriggerType


class Weekday(Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class ScheduleUnit(Enum):
    SECONDS = "seconds"
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"


class EventTrigger(BaseModel):
    type: EventTriggerType


class StoreTrigger(BaseModel):
    type: StoreTriggerType

    prefix: str = "/"
    initial: bool = False


class ScheduleTrigger(BaseModel):
    type: ScheduleTriggerType

    interval: int = 1
    interval_to: int | None = None
    once: bool = False
    at: str | None = Field(None, pattern=r"\d{2}:\d{2}(:\d{2})?|:\d{2}")
    until: datetime.datetime | datetime.time | datetime.timedelta | None = None
    unit: ScheduleUnit = ScheduleUnit.SECONDS
    start_day: Weekday = Weekday.MONDAY


Trigger = EventTrigger | StoreTrigger | ScheduleTrigger


class JobSpec(BaseModel):
    triggers: dict[str, Trigger] | None = None
    scale: int = 1
    recreate: bool = False
    build: bool = False
    container: Service


class TriggerInfo(BaseModel):
    id: str
    type: TriggerType
    time: datetime.datetime
    event: store.Event | None = None
    object: str | None = None


class JobInfo(BaseModel):
    name: str
    spec: JobSpec
    trigger: TriggerInfo | None = None

    @property
    def trigger_obj(self):
        if self.trigger is None or self.spec.triggers is None:
            return None

        return self.spec.triggers[self.trigger.id]
