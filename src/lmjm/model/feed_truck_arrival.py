import dataclasses
from typing import Optional

from lmjm.util.marshmallow_serializer import serialization_config


@dataclasses.dataclass
@serialization_config(skip_none_values=True)
class FeedTruckArrival:
    pk: str
    sk: str
    receive_date: str = ""
    fiscal_document_number: str = ""
    actual_amount_kg: int = 0
    feed_type: str = ""
    feed_description: str = ""
    feed_schedule_id: Optional[str] = None
