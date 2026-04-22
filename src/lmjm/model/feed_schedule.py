import dataclasses
from enum import StrEnum, auto
from typing import Optional

from lmjm.util.marshmallow_serializer import serialization_config


class FeedScheduleStatus(StrEnum):
    scheduled = auto()
    delivered = auto()
    canceled = auto()


@dataclasses.dataclass
@serialization_config(skip_none_values=True)
class FeedSchedule:
    pk: str
    sk: str
    feed_type: str = ""
    planned_date: str = ""
    expected_amount_kg: int = 0
    status: FeedScheduleStatus = FeedScheduleStatus.scheduled
    fulfilled_by: Optional[str] = None
    feed_description: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.status, str) and not isinstance(self.status, FeedScheduleStatus):
            self.status = FeedScheduleStatus(self.status)
