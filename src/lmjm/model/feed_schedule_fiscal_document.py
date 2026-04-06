import dataclasses
from typing import Optional

from lmjm.util.marshmallow_serializer import serialization_config


@dataclasses.dataclass
@serialization_config(skip_none_values=True)
class FeedScheduleFiscalDocument:
    pk: str
    sk: str
    fiscal_document_number: str = ""
    feed_schedule_id: Optional[str] = None
    status: str = "pending"
    product_code: str = ""
    actual_amount_kg: int = 0
    issue_date: str = ""
    planned_date: str = ""
