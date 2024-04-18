# SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
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


class Weekday(Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    STATURDAY = "staturday"
    SUNDAY = "sunday"


class ScheduleUnit(Enum):
    SECONDS = "seconds"
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"


class EventTrigger(BaseModel):
    id: str
    type: EventTriggerType


class StoreTrigger(BaseModel):
    id: str
    type: StoreTriggerType

    prefix: str = "/"


class ScheduleTrigger(BaseModel):
    id: str
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
    triggers: list[Trigger] = []
    scale: int = 1
    recreate: bool = False
    container: Service


class TriggerInfo(BaseModel):
    id: str
    time: datetime.datetime
    event: store.Event | None = None
    object: str | None = None


class JobInfo(BaseModel):
    name: str
    spec: JobSpec
    trigger: TriggerInfo | None = None
