import dataclasses
from decimal import Decimal
from typing import Optional

from lmjm.util.marshmallow_serializer import serialization_config


@dataclasses.dataclass
@serialization_config(skip_none_values=True)
class Batch:
    pk: str
    sk: str = "Batch"
    status: str = "created"
    supply_id: int = 0
    module_id: str = ""
    expected_slaughter_date: Optional[str] = None
    min_feed_stock_threshold: int = 0
    total_animal_count: Optional[int] = None
    average_start_date: Optional[str] = None
    distinct_origin_count: Optional[int] = None
    origin_types: Optional[list[str]] = None
    initial_animal_weight: Optional[Decimal] = None
    feed_leftover: Optional[Decimal] = None
