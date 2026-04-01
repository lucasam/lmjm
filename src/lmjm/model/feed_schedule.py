import dataclasses
from typing import Optional

from lmjm.util.marshmallow_serializer import serialization_config


@dataclasses.dataclass
@serialization_config(skip_none_values=True)
class FeedSchedule:
    pk: str
    sk: str
    feed_type: str = ""
    planned_date: str = ""
    expected_amount_kg: int = 0
    status: str = "scheduled"
    fulfilled_by: Optional[str] = None
